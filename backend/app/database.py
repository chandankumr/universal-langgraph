from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG  # Show SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Add this class for vector DB compatibility
class VectorDatabase:
    """Simple vector database wrapper for testing."""
    
    def __init__(self):
        self.docs = []
    
    def search(self, query: str, k: int = 5):
        """Mock search - returns empty list for now."""
        from langchain_core.documents import Document
        # Return empty list (works without actual vector DB setup)
        return []
    
    def add_documents(self, documents, collection_id=None):
        """Mock add documents."""
        return [f"doc_{i}" for i in range(len(documents))]

# Singleton instance
vector_db = VectorDatabase()

def get_db():
    """
    Dependency that provides a database session.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database tables.
    Call this once on startup.
    """
    try:
        # Import all models to ensure they're registered with Base
        from app import models
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
        # Test connection
        db = SessionLocal()
        # db.execute("SELECT 1")
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection tested successfully")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise

def check_health():
    """
    Check if database is healthy.
    Returns True if connection works, False otherwise.
    """
    try:
        db = SessionLocal()
        # db.execute("SELECT 1")
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False