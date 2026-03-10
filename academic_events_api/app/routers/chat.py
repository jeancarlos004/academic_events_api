from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.chat import (
    ChatAskRequest,
    ChatAskResponse,
    ChatConversationOut,
    ChatMessageOut,
    PaginatedChatConversations,
    PaginatedChatMessages,
)
from app.services.chat_service import ChatService


router = APIRouter(prefix="/chat", tags=["Chatbot"])


@router.post("/ask", response_model=ChatAskResponse)
async def ask_chatbot(
    body: ChatAskRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    msg = await ChatService.ask_and_store(
        db,
        question=body.question,
        user_id=current_user.id if current_user else None,
        conversation_id=body.conversation_id,
    )
    return {
        "id": msg.id,
        "user_id": msg.user_id,
        "conversation_id": msg.conversation_id,
        "question": msg.question,
        "answer": msg.answer,
        "model": msg.model,
        "created_at": msg.created_at,
    }


@router.get("/results", response_model=PaginatedChatMessages)
def list_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    total, items = ChatService.list_messages(db, page=page, page_size=page_size)
    results: list[ChatMessageOut] = [
        {
            "id": m.id,
            "user_id": m.user_id,
            "conversation_id": m.conversation_id,
            "question": m.question,
            "answer": m.answer,
            "model": m.model,
            "created_at": m.created_at,
        }
        for m in items
    ]
    return {"total": total, "page": page, "page_size": page_size, "results": results}


@router.get("/results/search", response_model=PaginatedChatMessages)
def search_results(
    q: Optional[str] = Query(None, description="Texto a buscar en pregunta/respuesta"),
    user_id: Optional[int] = Query(None, description="Filtrar por user_id"),
    model: Optional[str] = Query(None, description="Filtrar por modelo"),
    from_date: Optional[date] = Query(None, description="Desde (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Hasta (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    total, items = ChatService.search_messages(
        db,
        q=q,
        user_id=user_id,
        model=model,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    results: list[ChatMessageOut] = [
        {
            "id": m.id,
            "user_id": m.user_id,
            "conversation_id": m.conversation_id,
            "question": m.question,
            "answer": m.answer,
            "model": m.model,
            "created_at": m.created_at,
        }
        for m in items
    ]
    return {"total": total, "page": page, "page_size": page_size, "results": results}


@router.get("/conversations", response_model=PaginatedChatConversations)
def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    is_admin = getattr(current_user, "rol", None) == "admin"
    total, items = ChatService.list_conversations(
        db,
        page=page,
        page_size=page_size,
        user_id=current_user.id if current_user else None,
        is_admin=is_admin,
    )
    results: list[ChatConversationOut] = [
        {
            "conversation_id": r["conversation_id"],
            "user_id": r.get("user_id"),
            "messages_count": r["messages_count"],
            "last_message_at": r["last_message_at"],
        }
        for r in items
    ]
    return {"total": total, "page": page, "page_size": page_size, "results": results}


@router.get("/conversations/{conversation_id}", response_model=list[ChatMessageOut])
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    is_admin = getattr(current_user, "rol", None) == "admin"
    msgs = ChatService.get_conversation_messages(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id if current_user else None,
        is_admin=is_admin,
    )
    return [
        {
            "id": m.id,
            "user_id": m.user_id,
            "conversation_id": m.conversation_id,
            "question": m.question,
            "answer": m.answer,
            "model": m.model,
            "created_at": m.created_at,
        }
        for m in msgs
    ]


@router.get("/conversations/{conversation_id}/report.pdf")
def download_conversation_report(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    is_admin = getattr(current_user, "rol", None) == "admin"
    msgs = ChatService.get_conversation_messages(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id if current_user else None,
        is_admin=is_admin,
    )
    pdf_bytes = ChatService._build_conversation_pdf(conversation_id, msgs)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=conversacion_{conversation_id}.pdf"},
    )
