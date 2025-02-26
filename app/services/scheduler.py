from app.models.scheduler import ScheduledJob
from app.services import GoogleDriveManager
import logging
from datetime import datetime, timedelta
import re
from typing import List

class SchedulerService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.drive = GoogleDriveManager()

    def create_job(self, user_id: str, query: str, frequency: str, 
                  preferred_time: str, **params) -> ScheduledJob:
        """Create a new scheduled job with hourly validation"""
        # Validate time format and minutes
        if not re.match(r"^\d{2}:00$", preferred_time):
            raise ValueError("Scheduled times must be on the hour (HH:00)")
        
        # Validate frequency against minimum interval
        allowed_frequencies = ["daily", "weekly", "monthly"]
        if frequency not in allowed_frequencies:
            raise ValueError(f"Frequency must be one of {allowed_frequencies}")
        
        # Calculate next run time
        next_run = self._calculate_next_run(frequency, preferred_time)
        
        # Store job in database
        job = ScheduledJob(
            user_id=user_id,
            query_params={
                "query": query,
                "analysis_type": params.get("analysis_type", "report"),
                "views_filter": params.get("views_filter", 5000),
                "is_scheduled": True,
                "schedule_frequency": frequency,
                "preferred_time": preferred_time
            },
            frequency=frequency,
            preferred_time=preferred_time,
            next_run=next_run
        )
        
        # Add to database
        # (Implementation depends on your DB setup)
        return job

    def execute_job(self, job_id: int):
        """Execute a scheduled job and handle results"""
        # Get job from DB
        pass

    def _calculate_next_run(self, frequency: str, preferred_time: str) -> datetime:
        """Calculate next run time with hourly alignment"""
        now = datetime.now()
        hour = int(preferred_time.split(":")[0])
        
        base_time = now.replace(
            hour=hour,
            minute=0,
            second=0,
            microsecond=0
        )
        
        if frequency == "daily":
            if base_time > now:
                return base_time
            return base_time + timedelta(days=1)
        
        if frequency == "weekly":
            # Next same weekday
            return base_time + timedelta(weeks=1)
        
        if frequency == "monthly":
            # Same day next month
            try:
                return base_time.replace(month=base_time.month+1)
            except ValueError:
                return base_time.replace(year=base_time.year+1, month=1)
        
        raise ValueError(f"Unsupported frequency: {frequency}")

    def _send_notification(self, user_id: str, success: bool):
        """Integrate with your notification system"""
        # Would connect to email/SMS/WhatsApp service
        pass

    def get_due_jobs(self) -> List[ScheduledJob]:
        """Get jobs due in the current hour"""
        current_hour = datetime.now().replace(
            minute=0,
            second=0,
            microsecond=0
        )
        
        return Session().query(ScheduledJob).filter(
            ScheduledJob.next_run.between(
                current_hour,
                current_hour + timedelta(hours=1)
            ),
            ScheduledJob.is_active == True
        ).all()
