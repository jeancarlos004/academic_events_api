from __future__ import annotations

from datetime import date, datetime, time
from io import BytesIO
from typing import Optional
from uuid import uuid4

import httpx
import logging
import time as time_module
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import settings
from app.exceptions.app_exceptions import BadRequestException
from app.models.chat_message import ChatMessage


logger = logging.getLogger(__name__)


class ChatService:
    @staticmethod
    async def _ask_tinyllama(question: str) -> str:
        timeout = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)

        q_len = len(question or "")
        logger.info("chat.ask.start q_len=%s", q_len)

        # 0) Si existe COLAB_CHAT_URL, usamos el contrato del asistente (POST {message})
        if settings.COLAB_CHAT_URL:
            url = settings.COLAB_CHAT_URL.strip().strip('"').strip("'").rstrip("/")
            payload = {"message": question}
            logger.info("chat.provider.try provider=colab_chat_url url=%s", url)
            t0 = time_module.perf_counter()

            resp = None
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(
                        url,
                        json=payload,
                        headers={"ngrok-skip-browser-warning": "true"},
                    )
            except Exception:
                logger.exception("chat.provider.error provider=colab_chat_url")

            dt_ms = int((time_module.perf_counter() - t0) * 1000)
            if resp is not None:
                logger.info(
                    "chat.provider.done provider=colab_chat_url status=%s elapsed_ms=%s",
                    resp.status_code,
                    dt_ms,
                )

            if resp is not None and resp.status_code < 400:
                try:
                    data = resp.json()
                except Exception:
                    logger.exception("chat.provider.bad_json provider=colab_chat_url")
                    data = None

                answer = None
                if isinstance(data, dict):
                    answer = data.get("response") or data.get("answer") or data.get("text")

                # Si Colab respondió vacío/invalid, hacemos fallback al siguiente proveedor
                if isinstance(answer, str) and answer.strip():
                    logger.info("chat.ask.ok provider=colab_chat_url")
                    return answer.strip()
                logger.warning("chat.provider.empty_answer provider=colab_chat_url")
            elif resp is not None:
                logger.warning("chat.provider.http_error provider=colab_chat_url status=%s", resp.status_code)

        # 1) Si hay endpoint de Colab configurado, se prioriza
        if settings.COLAB_API:
            url = settings.COLAB_API.strip().strip('"').strip("'").rstrip("/")
            payload = {
                "question": question,
                "prompt": question,
                "model": settings.TINYLLAMA_MODEL,
                "stream": False,
            }

            logger.info("chat.provider.try provider=colab_api url=%s", url)
            t0 = time_module.perf_counter()

            resp = None
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(url, json=payload)
            except Exception:
                logger.exception("chat.provider.error provider=colab_api")

            dt_ms = int((time_module.perf_counter() - t0) * 1000)
            if resp is not None:
                logger.info(
                    "chat.provider.done provider=colab_api status=%s elapsed_ms=%s",
                    resp.status_code,
                    dt_ms,
                )

            if resp is not None and resp.status_code < 400:
                try:
                    data = resp.json()
                except Exception:
                    logger.exception("chat.provider.bad_json provider=colab_api")
                    data = None

                answer = None

                # Formatos comunes
                if isinstance(data, dict):
                    answer = data.get("answer") or data.get("response") or data.get("text")
                    # Formato OpenAI-like
                    if not answer and isinstance(data.get("choices"), list) and data["choices"]:
                        choice0 = data["choices"][0]
                        if isinstance(choice0, dict):
                            msg = choice0.get("message")
                            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                                answer = msg.get("content")

                if isinstance(answer, str) and answer.strip():
                    logger.info("chat.ask.ok provider=colab_api")
                    return answer.strip()
                logger.warning("chat.provider.empty_answer provider=colab_api")
            elif resp is not None:
                logger.warning("chat.provider.http_error provider=colab_api status=%s", resp.status_code)

        # 2) Fallback: Ollama local
        url = settings.OLLAMA_BASE_URL.rstrip("/") + "/api/generate"
        payload = {
            "model": settings.TINYLLAMA_MODEL,
            "prompt": question,
            "stream": False,
        }

        logger.info("chat.provider.try provider=ollama url=%s", url)
        t0 = time_module.perf_counter()

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(url, json=payload)
            except Exception:
                logger.exception("chat.provider.error provider=ollama")
                raise BadRequestException("No se pudo conectar al modelo TinyLlama (Ollama)")

        dt_ms = int((time_module.perf_counter() - t0) * 1000)
        logger.info("chat.provider.done provider=ollama status=%s elapsed_ms=%s", resp.status_code, dt_ms)

        if resp.status_code >= 400:
            raise BadRequestException("Error consultando TinyLlama")

        data = resp.json()
        answer = data.get("response")
        if not isinstance(answer, str) or not answer.strip():
            logger.error("chat.provider.empty_answer provider=ollama")
            raise BadRequestException(
                "No se obtuvo respuesta válida de ningún proveedor (COLAB_CHAT_URL/COLAB_API/Ollama)"
            )

        logger.info("chat.ask.ok provider=ollama")
        return answer.strip()

    @staticmethod
    async def ask_and_store(
        db: Session,
        question: str,
        user_id: Optional[int],
        conversation_id: Optional[str] = None,
    ) -> ChatMessage:
        answer = await ChatService._ask_tinyllama(question)

        conv_id = (conversation_id or "").strip() or str(uuid4())

        msg = ChatMessage(
            user_id=user_id,
            conversation_id=conv_id,
            question=question,
            answer=answer,
            model=settings.TINYLLAMA_MODEL,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def list_conversations(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[int] = None,
        is_admin: bool = False,
    ) -> tuple[int, list[dict]]:
        query = (
            db.query(
                ChatMessage.conversation_id.label("conversation_id"),
                func.max(ChatMessage.user_id).label("user_id"),
                func.count(ChatMessage.id).label("messages_count"),
                func.max(ChatMessage.created_at).label("last_message_at"),
            )
            .filter(ChatMessage.conversation_id.isnot(None))
        )

        if not is_admin and user_id is not None:
            query = query.filter(ChatMessage.user_id == user_id)

        query = query.group_by(ChatMessage.conversation_id)

        total = db.query(func.count()).select_from(query.subquery()).scalar() or 0

        rows = (
            query.order_by(func.max(ChatMessage.created_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = [
            {
                "conversation_id": r.conversation_id,
                "user_id": r.user_id,
                "messages_count": int(r.messages_count or 0),
                "last_message_at": r.last_message_at,
            }
            for r in rows
            if isinstance(r.conversation_id, str) and r.conversation_id.strip()
        ]
        return int(total), items

    @staticmethod
    def get_conversation_messages(
        db: Session,
        conversation_id: str,
        user_id: Optional[int] = None,
        is_admin: bool = False,
    ) -> list[ChatMessage]:
        conv_id = (conversation_id or "").strip()
        if not conv_id:
            raise BadRequestException("conversation_id inválido")

        query = db.query(ChatMessage).filter(ChatMessage.conversation_id == conv_id)
        if not is_admin and user_id is not None:
            query = query.filter(ChatMessage.user_id == user_id)

        return query.order_by(ChatMessage.created_at.asc()).all()

    @staticmethod
    def _build_conversation_pdf(conversation_id: str, messages: list[ChatMessage]) -> bytes:
        buf = BytesIO()

        doc = SimpleDocTemplate(
            buf,
            pagesize=LETTER,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=f"Conversación {conversation_id}",
        )

        styles = getSampleStyleSheet()

        title_style = styles["Title"].clone("chat_title")
        title_style.fontSize = 20
        title_style.leading = 24
        title_style.spaceAfter = 12

        h_style = styles["Heading3"].clone("chat_h3")
        h_style.spaceBefore = 8
        h_style.spaceAfter = 6

        label_style = styles["Normal"].clone("chat_label")
        label_style.fontSize = 10
        label_style.leading = 12

        body_style = styles["BodyText"].clone("chat_body")
        body_style.fontSize = 10
        body_style.leading = 13

        pre_style = styles["Code"].clone("chat_pre")
        pre_style.fontSize = 9
        pre_style.leading = 11

        story = []

        story.append(Paragraph("Reporte de Conversación", title_style))

        # Metadatos en tabla
        desde = str(messages[0].created_at) if messages else "—"
        hasta = str(messages[-1].created_at) if messages else "—"
        meta_table = Table(
            [
                [Paragraph("<b>ID</b>", label_style), Paragraph(conversation_id, label_style)],
                [Paragraph("<b>Mensajes</b>", label_style), Paragraph(str(len(messages)), label_style)],
                [Paragraph("<b>Desde</b>", label_style), Paragraph(desde, label_style)],
                [Paragraph("<b>Hasta</b>", label_style), Paragraph(hasta, label_style)],
            ],
            colWidths=[1.2 * inch, 5.55 * inch],
        )
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.lightgrey),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 0.25 * inch))

        context_marker = "\n\nContexto de eventos"

        for idx, m in enumerate(messages, start=1):
            header = f"<b>#{idx}</b> &nbsp;&nbsp; <b>Fecha:</b> {m.created_at}"
            if m.model:
                header += f" &nbsp;&nbsp; <b>Modelo:</b> {m.model}"
            story.append(Paragraph(header, h_style))

            raw_question = (m.question or "").strip()
            question_for_report = raw_question
            omitted_context = False
            if context_marker in raw_question:
                question_for_report = raw_question.split(context_marker, 1)[0].strip()
                omitted_context = True

            qa_table = Table(
                [
                    [
                        Paragraph("<b>Pregunta</b>", label_style),
                        Preformatted(question_for_report, pre_style),
                    ],
                    [
                        Paragraph("<b>Respuesta</b>", label_style),
                        Preformatted((m.answer or "").strip(), pre_style),
                    ],
                ],
                colWidths=[1.2 * inch, 5.55 * inch],
            )
            qa_table.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.6, colors.lightgrey),
                        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(qa_table)
            if omitted_context:
                story.append(
                    Paragraph(
                        "<i>Nota:</i> Se omitió el bloque de contexto de eventos para que el reporte sea más limpio.",
                        label_style,
                    )
                )
            story.append(Spacer(1, 0.18 * inch))

        doc.build(story)
        return buf.getvalue()

    @staticmethod
    def list_messages(db: Session, page: int = 1, page_size: int = 20) -> tuple[int, list[ChatMessage]]:
        q = db.query(ChatMessage)
        total = q.count()
        items = (
            q.order_by(ChatMessage.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, items

    @staticmethod
    def search_messages(
        db: Session,
        q: Optional[str] = None,
        user_id: Optional[int] = None,
        model: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[ChatMessage]]:
        query = db.query(ChatMessage)

        if q:
            like = f"%{q}%"
            query = query.filter(or_(ChatMessage.question.ilike(like), ChatMessage.answer.ilike(like)))

        if user_id is not None:
            query = query.filter(ChatMessage.user_id == user_id)

        if model:
            query = query.filter(ChatMessage.model == model)

        if from_date:
            query = query.filter(ChatMessage.created_at >= datetime.combine(from_date, time.min))

        if to_date:
            query = query.filter(ChatMessage.created_at <= datetime.combine(to_date, time.max))

        total = query.with_entities(func.count(ChatMessage.id)).scalar() or 0
        items = (
            query.order_by(ChatMessage.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return int(total), items
