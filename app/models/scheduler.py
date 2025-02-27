from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey
import enum
from app.models.database import Base
from sqlalchemy import Enum as SqlEnum  # Import SqlEnum like in messages.py

class JobFrequency(str, enum.Enum):  # Make it inherit from str like MessageStatus
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class JobStatus(str, enum.Enum):  # Make it inherit from str like MessageStatus
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
    frequency = Column(
        SqlEnum(JobFrequency, name="job_frequency", values_callable=lambda obj: [e.value for e in obj])
    )
    next_run = Column(DateTime)
    preferred_time = Column(String)  # Store as "HH:MM"
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    status = Column(
        SqlEnum(JobStatus, name="job_status", values_callable=lambda obj: [e.value for e in obj]), 
        default=JobStatus.PENDING
    )
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


