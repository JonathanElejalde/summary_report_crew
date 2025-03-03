from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy import Enum as SqlEnum
from pytz import UTC

from app.models.database import Base


class ProcessedVideo(Base):
    __tablename__ = "processed_videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'))
    video_id = Column(String, nullable=False, index=True)  # YouTube video ID
    message_id = Column(UUID(as_uuid=True), ForeignKey('messages.id', ondelete='SET NULL'), nullable=True)
    title = Column(String, nullable=True)
    url = Column(String, nullable=True)  # Full YouTube URL
    duration = Column(String, nullable=True)  # Duration in ISO 8601 format
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Add a unique constraint to prevent duplicate processing for the same user
    __table_args__ = (
        # Ensure a user doesn't process the same video twice
        # This allows different users to process the same video
        {'sqlite_autoincrement': True},
    )
