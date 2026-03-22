from sqlalchemy.orm import Session
from app.models import User
from app.schemas import UserCreate
from app.auth import get_password_hash
import logging

logger = logging.getLogger(__name__)

class UserService:
    """User management service."""
    
    def create_user(self, db: Session, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user exists
        existing_user = db.query(User).filter(
            User.email == user_data.email
        ).first()
        
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"Created new user: {user_data.email}")
        return db_user
    
    def get_user_by_email(self, db: Session, email: str) -> User:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, db: Session, user_id: str) -> User:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    def update_user(self, db: Session, user_id: str, updates: dict) -> User:
        """Update user information."""
        user = self.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")
        
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
        return user
    
    def delete_user(self, db: Session, user_id: str) -> bool:
        """Delete a user."""
        user = self.get_user_by_id(db, user_id)
        if not user:
            return False
        
        db.delete(user)
        db.commit()
        return True

user_service = UserService()