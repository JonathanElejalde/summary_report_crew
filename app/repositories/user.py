from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.user import User
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
        
    def get_or_create_user(self, phone_number: str) -> User:
        """Get or create a user by WhatsApp number"""
        try:
            user = self.db.get(User, phone_number)
            
            if not user:
                user = User(id=phone_number)
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info(f"Created new user: {phone_number}")
                
            return user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error getting/creating user {phone_number}: {str(e)}")
            raise
            
    def get_user_by_number(self, phone_number: str) -> Optional[User]:
        """Get user by WhatsApp number"""
        return self.db.get(User, phone_number)
