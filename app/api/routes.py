from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.core.processing import handle_analysis_request, handle_scheduled_analysis
import uuid
from app.repositories.scheduler import SchedulerService
from app.services.query_parser import parse_user_query, UserQueryParams

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
        
        if not params.is_scheduled:
            return await _handle_immediate_request(request, background_tasks)
        return await _handle_scheduled_request(request, params)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def _handle_immediate_request(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Handle immediate analysis request"""
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

async def _handle_scheduled_request(request: AnalysisRequest, params: UserQueryParams):
    """Handle scheduled analysis request"""
    scheduler = SchedulerService()
    try:
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
    finally:
        scheduler.close()

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
    scheduler = SchedulerService()
    try:
        due_jobs = scheduler.get_due_jobs()
        
        for job in due_jobs:
            # Update status to running
            scheduler.update_job_status(job.id, "running")
            
            # Queue job for processing
            background_tasks.add_task(
                process_scheduled_job,
                scheduler,  # Pass scheduler instance for status updates
                job.id,
                job.query_params,
                job.user_id
            )
        
        return {"status": "processing", "jobs_queued": len(due_jobs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        scheduler.close()

async def process_scheduled_job(scheduler: SchedulerService, job_id: int, query_params: dict, user_id: str):
    """Background task handler for scheduled jobs"""
    try:
        result = handle_scheduled_analysis(query_params)
        scheduler.update_job_status(job_id, "completed")
        print(f"Scheduled job {job_id} completed for user {user_id}")
    except Exception as e:
        scheduler.update_job_status(job_id, "failed")
        print(f"Scheduled job {job_id} failed: {str(e)}")
    finally:
        scheduler.close()
    
