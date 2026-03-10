from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


class ChatAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[str] = None


class ChatAskResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    conversation_id: Optional[str] = None
    question: str
    answer: str
    model: str
    created_at: datetime


class ChatMessageOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    conversation_id: Optional[str] = None
    question: str
    answer: str
    model: str
    created_at: datetime


class ChatConversationOut(BaseModel):
    conversation_id: str
    user_id: Optional[int] = None
    messages_count: int
    last_message_at: datetime


class PaginatedChatConversations(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[ChatConversationOut]


class ChatSearchParams(BaseModel):
    q: Optional[str] = None
    user_id: Optional[int] = None
    model: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None


class PaginatedChatMessages(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[ChatMessageOut]


class ChatConversationNLPGenerateRequest(BaseModel):
    target_lang: str = Field(default="en", min_length=2, max_length=16)
    force: bool = False


class ChatConversationNLPOut(BaseModel):
    conversation_id: str
    source_text: str
    summary: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    translation_lang: Optional[str] = None
    translation: Optional[str] = None
    sentiment_label: Optional[str] = None
    sentiment_polarity: Optional[float] = None
    sentiment_subjectivity: Optional[float] = None
    created_at: datetime
    updated_at: datetime
