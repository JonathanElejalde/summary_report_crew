from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.core.processing import handle_analysis_request
import uuid
from app.services.scheduler import SchedulerService
from app.services.query_parser import parse_user_query

router = APIRouter()

class AnalysisRequest(BaseModel):
    text: str
    user_id: str
    platform: str = "whatsapp"

@router.post("/analyze")
async def analyze_videos(
    request: AnalysisRequest, 
    background_tasks: BackgroundTasks
):
    """Handle both immediate and scheduled analysis requests"""
    try:
        # Parse user input to determine request type
        params = parse_user_query(request.text)
        
        if params.is_scheduled:
            # Handle scheduled request
            scheduler = SchedulerService()
            job = scheduler.create_job(
                user_id=request.user_id,
                query=params.query,
                frequency=params.schedule_frequency,
                preferred_time=params.preferred_time,
                analysis_type=params.analysis_type,
                views_filter=params.views_filter
            )
            
            return {
                "status": "scheduled",
                "job_id": job.id,
                "next_run": job.next_run.isoformat(),
                "message": f"Analysis scheduled {params.schedule_frequency} at {params.preferred_time}"
            }
        else:
            # Handle immediate request
            task_id = str(uuid.uuid4())
            background_tasks.add_task(
                process_and_store_result,
                task_id,
                request.text,
                request.user_id
            )
            
            return {
                "status": "processing",
                "task_id": task_id,
                "message": "Analysis started in background"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def process_and_store_result(task_id: str, user_input: str, user_id: str):
    """Background task handler"""
    try:
        result = handle_analysis_request(user_input)
        # Store result in database/filesystem here
        # For now, we'll just log it
        print(f"Task {task_id} completed for user {user_id}")
    except Exception as e:
        print(f"Task {task_id} failed: {str(e)}")

@router.post("/execute-scheduled")
async def execute_scheduled_jobs(background_tasks: BackgroundTasks):
    """Endpoint for scheduler to trigger stored jobs"""
    try:
        scheduler = SchedulerService()
        due_jobs = scheduler.get_due_jobs()
        
        for job in due_jobs:
            background_tasks.add_task(
                process_and_store_result,
                f"job-{job.id}",  # Generate task ID from job ID
                job.query_params["query"],  # Use stored query
                job.user_id
            )
            # Update job status after queuing
            scheduler.update_job_status(job.id, "queued")
        
        return {"status": "processing", "jobs_queued": len(due_jobs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
