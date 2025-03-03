from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.messages import WhatsAppMessage, MessageStatus


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, user_id: str, user_message: Optional[str] = None, 
               agent_message: Optional[str] = None, media_urls: Optional[dict] = None,
               status: MessageStatus = MessageStatus.RECEIVED) -> WhatsAppMessage:
        """Create a new WhatsApp message record"""
        message = WhatsAppMessage(
            user_id=user_id,
            user_message=user_message,
            agent_message=agent_message,
            media_urls=media_urls or {},
            status=status
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def get_by_id(self, id: UUID) -> Optional[WhatsAppMessage]:
        """Get a message by its ID"""
        return self.db.query(WhatsAppMessage).filter(WhatsAppMessage.id == id).first()
    
    def get_by_user_id(self, user_id: str) -> List[WhatsAppMessage]:
        """Get all messages for a specific user"""
        return self.db.query(WhatsAppMessage).filter(WhatsAppMessage.user_id == user_id).all()
    
    def update_status(self, id: UUID, status: MessageStatus) -> Optional[WhatsAppMessage]:
        """Update the status of a message"""
        message = self.get_by_id(id)
        if message:
            message.status = status
            self.db.commit()
            self.db.refresh(message)
        return message
    
    def update_agent_message(self, id: UUID, agent_message: str) -> Optional[WhatsAppMessage]:
        """Update the agent's response message"""
        message = self.get_by_id(id)
        if message:
            message.agent_message = agent_message
            self.db.commit()
            self.db.refresh(message)
        return message
    
    def update_media_urls(self, id: UUID, media_urls: dict) -> Optional[WhatsAppMessage]:
        """Update the media URLs for a message"""
        message = self.get_by_id(id)
        if message:
            message.media_urls = media_urls
            self.db.commit()
            self.db.refresh(message)
        return message
    
    def delete(self, id: UUID) -> bool:
        """Delete a message record"""
        message = self.get_by_id(id)
        if message:
            self.db.delete(message)
            self.db.commit()
            return True
        return False
