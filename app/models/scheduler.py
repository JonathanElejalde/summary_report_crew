from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Enum
import enum
from app.models.database import Base

class JobFrequency(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class JobStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEACTIVATED = "deactivated"

class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'))
    query_params = Column(JSON)  # Stores serialized UserQueryParams
    frequency = Column(Enum(JobFrequency))  # Using enum
    next_run = Column(DateTime)
    preferred_time = Column(String)  # Store as "HH:MM"
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)  # Using enum
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


