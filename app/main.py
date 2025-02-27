from fastapi import FastAPI
from dotenv import load_dotenv
import agentops
import os
from app.api.agent import router as analysis_router
from app.api.twilio_router import router as twilio_router
# Load environment variables first
load_dotenv()

# # Initialize tracking
# agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

# Create FastAPI app
app = FastAPI(
    title="YouTube Analysis API",
    description="API for analyzing YouTube videos and generating reports",
    version="0.1.0",
    docs_url="/docs"
)

# Include routers
app.include_router(analysis_router, prefix="/api/v1", tags=["analysis"])
app.include_router(twilio_router, prefix="/api/v1", tags=["twilio"])

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "version": app.version,
        "environment": os.getenv("ENVIRONMENT", "development")
    }


