from __future__ import annotations

import json
import re
from collections import Counter
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
from app.models.chat_conversation_nlp import ChatConversationNLP
from app.models.chat_message import ChatMessage


logger = logging.getLogger(__name__)


class ChatService:
    _ES_STOPWORDS = {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "y",
        "o",
        "de",
        "del",
        "al",
        "en",
        "por",
        "para",
        "con",
        "sin",
        "sobre",
        "a",
        "e",
        "u",
        "que",
        "como",
        "cuando",
        "donde",
        "cual",
        "cuales",
        "quien",
        "quienes",
        "es",
        "son",
        "ser",
        "fue",
        "fueron",
        "era",
        "eran",
        "se",
        "su",
        "sus",
        "mi",
        "mis",
        "tu",
        "tus",
        "ya",
        "no",
        "si",
        "más",
        "mas",
        "menos",
        "muy",
        "también",
        "tambien",
        "pero",
        "porque",
        "qué",
        "que",
        "cómo",
        "como",
    }

    _EN_STOPWORDS = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "with",
        "without",
        "at",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "it",
        "this",
        "that",
        "these",
        "those",
        "as",
        "not",
        "no",
        "yes",
        "very",
        "also",
        "but",
        "because",
        "what",
        "how",
        "when",
        "where",
        "who",
        "which",
    }

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
    def _build_nlp_source_text(messages: list[ChatMessage]) -> str:
        parts: list[str] = []
        for m in messages:
            ans = (m.answer or "").strip()
            if ans:
                parts.append(ans)
        return "\n\n".join(parts).strip()

    @staticmethod
    def _extract_keywords(text: str, limit: int = 12) -> list[str]:
        if not isinstance(text, str) or not text.strip():
            return []

        tokens = re.findall(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]{3,}", text.lower())
        stop = ChatService._ES_STOPWORDS | ChatService._EN_STOPWORDS
        filtered = [t for t in tokens if t not in stop]
        if not filtered:
            return []

        counts = Counter(filtered)
        return [w for (w, _) in counts.most_common(limit)]

    @staticmethod
    def _extract_keywords_spacy_nltk(text: str, limit: int = 12) -> list[str]:
        if not isinstance(text, str) or not text.strip():
            return []

        try:
            import spacy
            from nltk import FreqDist
        except Exception:
            return []

        # Stopwords (si NLTK stopwords no está disponible, usamos las internas)
        stop: set[str] = set()
        try:
            from nltk.corpus import stopwords

            stop = set(stopwords.words("spanish")) | set(stopwords.words("english"))
        except Exception:
            stop = ChatService._ES_STOPWORDS | ChatService._EN_STOPWORDS

        # Intentamos cargar un modelo español; si no existe, usamos blank("es")
        try:
            nlp = spacy.load("es_core_news_sm")
        except Exception:
            nlp = spacy.blank("es")

        doc = nlp(text)

        tokens: list[str] = []
        for t in doc:
            if t.is_space or t.is_punct or t.like_num:
                continue

            raw = (t.lemma_ or t.text or "").strip().lower()
            if len(raw) < 3:
                continue
            if raw in stop:
                continue
            # Evitar tokens con caracteres raros
            if not re.fullmatch(r"[a-záéíóúñü]+", raw):
                continue
            tokens.append(raw)

        if not tokens:
            return []

        fd = FreqDist(tokens)
        return [w for (w, _) in fd.most_common(limit)]

    @staticmethod
    def _analyze_sentiment_textblob(text: str) -> tuple[Optional[str], Optional[float], Optional[float]]:
        if not isinstance(text, str) or not text.strip():
            return None, None, None
        try:
            from textblob import TextBlob
        except Exception:
            return None, None, None

        try:
            blob = TextBlob(text)
            polarity = float(blob.sentiment.polarity)
            subjectivity = float(blob.sentiment.subjectivity)
        except Exception:
            return None, None, None

        if polarity > 0.1:
            label = "positivo"
        elif polarity < -0.1:
            label = "negativo"
        else:
            label = "neutral"

        return label, polarity, subjectivity

    @staticmethod
    def _try_transformers_summarize_and_translate(text: str, target_lang: str) -> tuple[Optional[str], Optional[str]]:
        if not isinstance(text, str) or not text.strip():
            return None, None

        try:
            from transformers import pipeline
        except Exception:
            return None, None

        # Resumen (modelo liviano, puede requerir descarga). Si falla, devolvemos None.
        summary: Optional[str] = None
        try:
            summarizer = pipeline(
                "summarization",
                model="sshleifer/distilbart-cnn-12-6",
            )
            out = summarizer(text[:4000], max_length=180, min_length=60, do_sample=False)
            if isinstance(out, list) and out and isinstance(out[0], dict):
                summary = (out[0].get("summary_text") or "").strip() or None
        except Exception:
            summary = None

        if not summary:
            return None, None

        lang = (target_lang or "").strip() or "en"
        translation: Optional[str] = None
        try:
            # Traducción desde ES -> target. Si el resumen no está en ES (por el modelo), igual traduce.
            if lang == "en":
                model_name = "Helsinki-NLP/opus-mt-es-en"
            elif lang == "pt":
                model_name = "Helsinki-NLP/opus-mt-es-pt"
            elif lang == "fr":
                model_name = "Helsinki-NLP/opus-mt-es-fr"
            elif lang == "it":
                model_name = "Helsinki-NLP/opus-mt-es-it"
            else:
                model_name = "Helsinki-NLP/opus-mt-es-en"

            translator = pipeline("translation", model=model_name)
            out_t = translator(summary, max_length=220)
            if isinstance(out_t, list) and out_t and isinstance(out_t[0], dict):
                translation = (out_t[0].get("translation_text") or "").strip() or None
        except Exception:
            translation = None

        return summary, translation

    @staticmethod
    async def _summarize_and_translate_text(text: str, target_lang: str) -> tuple[str, str]:
        lang = (target_lang or "").strip() or "en"
        prompt = (
            "A partir del siguiente TEXTO, genera un resumen en español y su traducción. "
            "Devuelve ÚNICAMENTE un JSON válido con esta forma exacta:\n"
            "{\"summary_es\": \"...\", \"translation\": \"...\", \"translation_lang\": \"...\"}\n\n"
            "Reglas:\n"
            "- summary_es: 5 a 10 líneas máximo, claro y profesional.\n"
            f"- translation: traducción de summary_es al idioma '{lang}', sin explicaciones.\n"
            f"- translation_lang: '{lang}'.\n\n"
            "TEXTO:\n"
            f"{text}"
        )

        raw = await ChatService._ask_tinyllama(prompt)
        try:
            data = json.loads(raw)
            summary = (data.get("summary_es") or "").strip()
            translation = (data.get("translation") or "").strip()
        except Exception:
            summary = raw.strip()
            translation = ""

        return summary, translation

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
    def get_conversation_nlp(db: Session, conversation_id: str) -> Optional[ChatConversationNLP]:
        conv_id = (conversation_id or "").strip()
        if not conv_id:
            raise BadRequestException("conversation_id inválido")
        return db.query(ChatConversationNLP).filter(ChatConversationNLP.conversation_id == conv_id).first()

    @staticmethod
    async def generate_conversation_nlp(
        db: Session,
        conversation_id: str,
        user_id: Optional[int],
        is_admin: bool,
        target_lang: str = "en",
        force: bool = False,
    ) -> ChatConversationNLP:
        conv_id = (conversation_id or "").strip()
        if not conv_id:
            raise BadRequestException("conversation_id inválido")

        existing = db.query(ChatConversationNLP).filter(ChatConversationNLP.conversation_id == conv_id).first()
        if existing is not None and not force:
            return existing

        msgs = ChatService.get_conversation_messages(
            db,
            conversation_id=conv_id,
            user_id=user_id,
            is_admin=is_admin,
        )
        if not msgs:
            raise BadRequestException("No hay mensajes para analizar")

        source_text = ChatService._build_nlp_source_text(msgs)
        if not source_text:
            raise BadRequestException("No hay texto de respuesta del chatbot para analizar")

        # Optimización: recortar texto para reducir latencia/costo
        max_chars = 6000
        if len(source_text) > max_chars:
            source_text = source_text[:max_chars]

        # 1) Resumen+traducción: intentamos con Transformers (si hay modelos), si falla usamos LLM.
        summary_t, translation_t = ChatService._try_transformers_summarize_and_translate(source_text, target_lang=target_lang)
        if summary_t:
            summary = summary_t
            translation = translation_t or ""
        else:
            summary, translation = await ChatService._summarize_and_translate_text(source_text, target_lang=target_lang)

        # 2) Keywords: intentamos spaCy+NLTK, fallback a método simple.
        keywords = ChatService._extract_keywords_spacy_nltk(source_text)
        if not keywords:
            keywords = ChatService._extract_keywords(source_text)

        # 3) Sentimiento (TextBlob)
        s_label, s_pol, s_subj = ChatService._analyze_sentiment_textblob(source_text)

        if existing is None:
            row = ChatConversationNLP(
                conversation_id=conv_id,
                source_text=source_text,
                summary=summary,
                keywords=json.dumps(keywords, ensure_ascii=False),
                translation_lang=(target_lang or "").strip() or None,
                translation=translation,
                sentiment_label=s_label,
                sentiment_polarity=s_pol,
                sentiment_subjectivity=s_subj,
            )
            db.add(row)
        else:
            row = existing
            row.source_text = source_text
            row.summary = summary
            row.keywords = json.dumps(keywords, ensure_ascii=False)
            row.translation_lang = (target_lang or "").strip() or None
            row.translation = translation
            row.sentiment_label = s_label
            row.sentiment_polarity = s_pol
            row.sentiment_subjectivity = s_subj

        db.commit()
        db.refresh(row)
        return row

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
        body_style.wordWrap = "LTR"
        body_style.splitLongWords = 1

        pre_style = styles["Code"].clone("chat_pre")
        pre_style.fontSize = 9
        pre_style.leading = 11

        def _p(text: str) -> Paragraph:
            from xml.sax.saxutils import escape

            raw = (text or "").strip()
            # Insertar puntos de corte en tokens muy largos para evitar que se salgan del recuadro
            parts: list[str] = []
            for tok in raw.split():
                if len(tok) > 50:
                    chunks = [tok[i : i + 25] for i in range(0, len(tok), 25)]
                    parts.append("\u200b".join(chunks))
                else:
                    parts.append(tok)
            raw = " ".join(parts)

            safe = escape(raw)
            safe = safe.replace("\n", "<br/>")
            return Paragraph(safe or "—", body_style)

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
                        _p(question_for_report),
                    ],
                    [
                        Paragraph("<b>Respuesta</b>", label_style),
                        _p((m.answer or "").strip()),
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
                        ("WORDWRAP", (1, 0), (1, -1), "LTR"),
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
