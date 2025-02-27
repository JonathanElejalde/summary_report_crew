from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime
from app.models.database import Base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON, ForeignKey, text
from enum import Enum
from sqlalchemy import Enum as SqlEnum

class MessageStatus(str, Enum):
    RECEIVED = "received"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

class WhatsAppMessage(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'))
    direction = Column(String, index=True)  # 'inbound' or 'outbound'
    body = Column(String)
    media_urls = Column(JSON)
    status = Column(
        SqlEnum(MessageStatus, name="message_status", values_callable=lambda obj: [e.value for e in obj]),
        default=MessageStatus.RECEIVED,
        nullable=False
    )
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
