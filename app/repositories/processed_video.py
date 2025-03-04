from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID

from app.models.processed_video import ProcessedVideo


class ProcessedVideoRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, user_id: str, video_id: str, message_id: Optional[UUID] = None, 
               title: Optional[str] = None, url: Optional[str] = None,
               duration: Optional[str] = None) -> ProcessedVideo:
        """Create a new processed video record"""
        # Check if this video has already been processed for this user
        existing = self.get_by_user_and_video_id(user_id, video_id)
        if existing:
            # Video already processed, return the existing record
            return existing
        
        processed_video = ProcessedVideo(
            user_id=user_id,
            video_id=video_id,
            message_id=message_id,
            title=title,
            url=url,
            duration=duration
        )
        self.db.add(processed_video)
        self.db.commit()
        self.db.refresh(processed_video)
        return processed_video
    
    def get_by_id(self, id: UUID) -> Optional[ProcessedVideo]:
        """Get a processed video by its ID"""
        return self.db.query(ProcessedVideo).filter(ProcessedVideo.id == id).first()
    
    def get_by_user_and_video_id(self, user_id: str, video_id: str) -> Optional[ProcessedVideo]:
        """Check if a video has been processed by a specific user"""
        return self.db.query(ProcessedVideo).filter(
            and_(
                ProcessedVideo.user_id == user_id,
                ProcessedVideo.video_id == video_id
            )
        ).first()
    
    def get_by_user_id(self, user_id: str) -> List[ProcessedVideo]:
        """Get all videos processed by a specific user"""
        return self.db.query(ProcessedVideo).filter(ProcessedVideo.user_id == user_id).all()
    
    def get_processed_video_ids_by_user(self, user_id: str) -> List[str]:
        """Get all video IDs processed by a specific user"""
        results = self.db.query(ProcessedVideo.video_id).filter(ProcessedVideo.user_id == user_id).all()
        return [result[0] for result in results]
    
    def delete(self, id: UUID) -> bool:
        """Delete a processed video record"""
        processed_video = self.get_by_id(id)
        if processed_video:
            self.db.delete(processed_video)
            self.db.commit()
            return True
        return False
