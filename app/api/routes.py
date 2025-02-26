from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.core.processing import handle_analysis_request
import uuid

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
    """Initiate background analysis"""
    try:
        # Store the task in memory (replace with database in production)
        task_id = str(uuid.uuid4())
        
        # Add to background tasks
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
    
