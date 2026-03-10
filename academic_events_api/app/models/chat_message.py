from sqlalchemy import Column, Integer, Text, ForeignKey, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base_model import TimestampMixin


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    conversation_id = Column(String(36), nullable=True, index=True)

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    model = Column(String(100), nullable=False, default="tinyllama")

    user = relationship("User")
