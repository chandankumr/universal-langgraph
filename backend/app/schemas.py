from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# ===========================
# AUTH SCHEMAS
# ===========================

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

# ===========================
# API KEY SCHEMAS
# ===========================

class APIKeyCreate(BaseModel):
    provider: str
    api_key: str

class APIKeyResponse(BaseModel):
    id: str
    provider: str
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime] = None

# ===========================
# VECTOR DB SCHEMAS
# ===========================

class VectorDBConfigCreate(BaseModel):
    db_type: str
    config: Dict[str, Any]
    collection_name: Optional[str] = "default"

class DeploymentRequest(BaseModel):
    db_type: str

class DeploymentResponse(BaseModel):
    success: bool
    message: str
    status: str
    access_url: Optional[str] = None

# ===========================
# QUERY SCHEMAS
# ===========================

class QueryRequest(BaseModel):
    question: str
    thread_id: Optional[str] = None
    collection_filter: Optional[str] = None
    conversation_history: Optional[List[dict]] = None
    provider: Optional[str] = "openai"

class QueryResponse(BaseModel):
    thread_id: str
    question: str
    answer: str
    router_decision: str = "search"
    documents_retrieved: int = 0
    iterations: int = 0
    status: str = "success"

# ===========================
# DOCUMENT SCHEMAS
# ===========================

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    status: str

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    chunk_count: int
    status: str
    created_at: datetime

# ===========================
# CONVERSATION SCHEMAS
# ===========================

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

class ResearchRequest(BaseModel):
    goal: str