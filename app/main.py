from fastapi import FastAPI
from dotenv import load_dotenv
import agentops
import os
from contextlib import asynccontextmanager

from app.api.routes import router as analysis_router
from app.services.scheduler import SchedulerService

# Load environment variables first
load_dotenv()

# Initialize tracking
agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize scheduler on startup"""
    scheduler = SchedulerService()
    scheduler.initialize()
    yield

# Create FastAPI app with lifespan
app = FastAPI(
    title="YouTube Analysis API",
    description="API for analyzing YouTube videos and generating reports",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan
)

# Include routers
app.include_router(analysis_router, prefix="/api/v1", tags=["analysis"])

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "version": app.version,
        "environment": os.getenv("ENVIRONMENT", "development")
    }
