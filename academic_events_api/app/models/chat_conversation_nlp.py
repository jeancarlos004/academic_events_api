from sqlalchemy import Column, Float, Integer, String, Text, UniqueConstraint

from app.core.database import Base
from app.models.base_model import TimestampMixin


class ChatConversationNLP(Base, TimestampMixin):
    __tablename__ = "chat_conversation_nlp"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(36), nullable=False, index=True)

    # Texto base usado en el análisis (normalmente solo respuestas del bot)
    source_text = Column(Text, nullable=False)

    # Resultados
    summary = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)  # JSON string (lista)
    translation_lang = Column(String(16), nullable=True)
    translation = Column(Text, nullable=True)

    sentiment_label = Column(String(32), nullable=True)
    sentiment_polarity = Column(Float, nullable=True)
    sentiment_subjectivity = Column(Float, nullable=True)

    __table_args__ = (UniqueConstraint("conversation_id", name="uq_chat_conversation_nlp_conversation_id"),)
