from sqlalchemy import create_engine
from app.models import Base
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
Base.metadata.create_all(engine)

print("✅ Database tables created!")