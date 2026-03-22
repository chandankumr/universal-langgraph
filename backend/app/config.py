import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Optional
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Universal LangGraph Platform"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week
    
    # Database
    # DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/langgraph_platform"
    # DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/langgraph_platform"
    # DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/langgraph_platform"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/langgraph_platform"
    
    # Encryption for API Keys
    ENCRYPTION_KEY: str = "32-byte-encryption-key-here!"  # Must be 32 bytes
    
    # Supported LLM Providers
    SUPPORTED_LLM_PROVIDERS: list = ["openai", "anthropic", "google", "ollama", "groq", "mistral"]
    
    # Supported Vector DBs
    SUPPORTED_VECTOR_DBS: list = ["chroma", "pinecone", "qdrant", "weaviate", "milvus"]
    
    # Default Limits
    MAX_FILE_SIZE_MB: int = 50
    MAX_DOCUMENTS_PER_USER: int = 1000
    MAX_QUERIES_PER_DAY: int = 1000
    
    # class Config:
    #     env_file = ".env"
    #     case_sensitive = True

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"   # ✅ THIS FIXES YOUR ERROR
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()