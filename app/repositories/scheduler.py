from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.scheduler import ScheduledJob, JobFrequency, JobStatus
import logging
from datetime import datetime, timedelta
from typing import List, Optional

class SchedulerService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._db: Optional[Session] = None

    @property
    def db(self) -> Session:
        """Get database session"""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def close(self):
        """Close database session"""
        if self._db is not None:
            self._db.close()
            self._db = None

    def create_job(self, user_id: str, query: str, frequency: str, 
                  preferred_time: str, **params) -> ScheduledJob:
        """Create a new scheduled job"""
        try:
            job = self._create_job_internal(user_id, query, frequency, preferred_time, **params)
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            return job
        except Exception as e:
            self.db.rollback()
            raise e

    def _create_job_internal(self, user_id: str, query: str, frequency: str, 
                            preferred_time: str, **params) -> ScheduledJob:
        """Internal method to create job without database operations"""
        # Adjust time to next hour if not on the hour
        hour = preferred_time.split(":")[0]
        preferred_time = f"{hour}:00"
        
        # Validate frequency using enum
        job_frequency = JobFrequency(frequency)  # Will raise ValueError if invalid
        
        # Calculate next run time
        next_run = self._calculate_next_run(frequency, preferred_time)
        
        # Create and return job
        return ScheduledJob(
            user_id=user_id,
            query_params={
                "query": query,
                "analysis_type": params.get("analysis_type", "report"),
                "views_filter": params.get("views_filter", 5000),
                "is_scheduled": True,
                "schedule_frequency": frequency,
                "preferred_time": preferred_time
            },
            frequency=job_frequency,
            preferred_time=preferred_time,
            next_run=next_run,
            status=JobStatus.PENDING,
            is_active=True
        )

    def get_due_jobs(self) -> List[ScheduledJob]:
        """Get pending jobs due for execution from previous hour and current hour"""
        try:
            current_hour = datetime.now().replace(
                minute=0,
                second=0,
                microsecond=0
            )
            previous_hour = current_hour - timedelta(hours=1)
            next_hour = current_hour + timedelta(hours=1)
            
            return self.db.query(ScheduledJob).filter(
                # Get jobs between previous hour and next hour
                ScheduledJob.next_run.between(previous_hour, next_hour),
                ScheduledJob.is_active == True,
                ScheduledJob.status == JobStatus.PENDING  # Only get pending jobs
            ).order_by(ScheduledJob.next_run).all()
            
        except Exception as e:
            self.logger.error(f"Error getting due jobs: {e}")
            return []

    def update_job_status(self, job_id: int, status: str) -> bool:
        """Update job status and next run time"""
        try:
            return self._update_job_status_internal(job_id, status)
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error updating job {job_id}: {e}")
            return False

    def _update_job_status_internal(self, job_id: int, status: str) -> bool:
        """Internal method to update job status"""
        job = self.db.get(ScheduledJob, job_id)
        if not job:
            return False
        
        job_status = JobStatus(status)  # Will raise ValueError if invalid
        job.status = job_status
        
        if job_status == JobStatus.COMPLETED:
            # Calculate next run based on frequency
            job.last_run = datetime.now()
            job.next_run = self._calculate_next_run(
                job.frequency.value, 
                job.preferred_time
            )
            job.retry_count = 0
        elif job_status == JobStatus.FAILED:
            job.retry_count += 1
            if job.retry_count >= 3:
                job.is_active = False
                job.status = JobStatus.DEACTIVATED
                self._send_notification(job.user_id, False)
        
        self.db.commit()
        return True

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
        
        if base_time <= now:
            if frequency == "daily":
                base_time += timedelta(days=1)
            elif frequency == "weekly":
                base_time += timedelta(weeks=1)
            elif frequency == "monthly":
                # Handle month rollover
                if base_time.month == 12:
                    base_time = base_time.replace(year=base_time.year + 1, month=1)
                else:
                    base_time = base_time.replace(month=base_time.month + 1)
        
        return base_time

    def _send_notification(self, user_id: str, success: bool):
        """Send notification about job status"""
        # TODO: Implement notification system
        pass


if __name__ == "__main__":
    # Test scheduler functionality
    scheduler = SchedulerService()
    try:
        print("\n=== Testing Scheduler Service ===")
        
        # Test 1: Create jobs with different schedules
        test_jobs = [
            {
                "user_id": "test_user_1",
                "query": "AI news",
                "frequency": "daily",
                "preferred_time": "09:30",
                "analysis_type": "summary"
            },
            {
                "user_id": "test_user_2",
                "query": "Machine Learning tutorials",
                "frequency": "weekly",
                "preferred_time": "14:00",
                "analysis_type": "report"
            }
        ]
        
        created_jobs = []
        print("\n1. Creating test jobs...")
        for job_data in test_jobs:
            job = scheduler.create_job(**job_data)
            created_jobs.append(job)
            print(f"\nCreated job:")
            print(f"- ID: {job.id}")
            print(f"- Query: {job.query_params['query']}")
            print(f"- Schedule: {job.frequency} at {job.preferred_time}")
            print(f"- Next run: {job.next_run}")
        
        # Test 2: Get due jobs
        print("\n2. Checking due jobs...")
        due_jobs = scheduler.get_due_jobs()
        print(f"Found {len(due_jobs)} jobs due for execution")
        for job in due_jobs:
            print(f"- Job {job.id}: {job.query_params['query']}")
        
        # Test 3: Update job status
        print("\n3. Testing status updates...")
        if created_jobs:
            test_job = created_jobs[0]
            print(f"Updating job {test_job.id} status to 'running'")
            scheduler.update_job_status(test_job.id, "running")
            print(f"Updating job {test_job.id} status to 'completed'")
            scheduler.update_job_status(test_job.id, "completed")
            print(f"New next_run time: {test_job.next_run}")
        
        # Test 4: Test past due jobs
        print("\n4. Testing past due jobs...")
        # Create jobs with different timestamps
        current_time = datetime.now()

        # Job from 2 hours ago (should not be retrieved)
        old_job = scheduler.create_job(
            user_id="test_user_1",
            query="Too old job",
            frequency="daily",
            preferred_time="01:00",
            analysis_type="summary"
        )
        old_job.next_run = current_time - timedelta(hours=2)

        # Job from previous hour (should be retrieved)
        past_job = scheduler.create_job(
            user_id="test_user_1",
            query="Previous hour job",
            frequency="daily",
            preferred_time="01:00",
            analysis_type="summary"
        )
        past_job.next_run = current_time - timedelta(minutes=30)

        scheduler.db.commit()

        # Check if we can retrieve only the appropriate jobs
        due_jobs = scheduler.get_due_jobs()
        print(f"\nFound {len(due_jobs)} jobs due for execution (from last hour to next hour)")
        for job in due_jobs:
            print(f"- Job {job.id}: {job.query_params['query']} (scheduled for: {job.next_run})")
        
        print("\n=== Test completed successfully ===")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
    finally:
        scheduler.close()