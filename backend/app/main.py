from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import json
from fastapi.responses import StreamingResponse

from app.config import settings
# from app.database import get_db
from app.database import get_db, init_db, Base, engine
from app.models import User
from app.auth import get_current_user, authenticate_user, create_access_token
from app.services.llm_service import llm_service
from app.services.vector_service import vector_service
from app.services.deployment_service import deployment_service
from app.services.graph_service import graph_service
from app.schemas import (
    UserCreate, UserLogin, APIKeyCreate, VectorDBConfigCreate,
    QueryRequest, QueryResponse, DeploymentRequest, DeploymentResponse, ResearchRequest, Token
)
# from app.graphs import auto_research_graph

# Setup
app = FastAPI(
    title=settings.APP_NAME,
    description="Universal LangGraph Platform - Bring Your Own Keys & GPU",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
logger = logging.getLogger(__name__)

# ==============================================================================
# AUTH ENDPOINTS
# ==============================================================================

@app.post("/api/v1/auth/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Login and get JWT token."""
    user = authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/auth/register", response_model=Dict[str, Any])
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register new user."""
    from app.services.user_service import user_service
    
    try:
        user = user_service.create_user(db, user_data)
        return {"message": "User created successfully", "email": user.email}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==============================================================================
# API KEY MANAGEMENT
# ==============================================================================

@app.post("/api/v1/keys", response_model=Dict[str, Any])
async def add_api_key(
    # key_ APIKeyCreate,
    key: APIKeyCreate,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Add API key for a provider (encrypted)."""
    # Encrypt and store
    pass

@app.get("/api/v1/keys", response_model=List[Dict[str, Any]])
async def list_api_keys(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """List all configured API keys (masked)."""
    pass

@app.delete("/api/v1/keys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete API key."""
    pass

@app.post("/api/v1/keys/test/{provider}")
async def test_api_key(
    provider: str,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Test API key connection."""
    return llm_service.test_connection(db, current_user.id, provider)

# ==============================================================================
# VECTOR DB MANAGEMENT
# ==============================================================================

@app.get("/api/v1/vector-dbs/supported", response_model=List[Dict[str, Any]])
async def list_supported_vector_dbs():
    """List all supported vector databases."""
    return [
        {"type": db, "config": vector_service.get_deployment_config(db)}
        for db in vector_service.supported_dbs
    ]

@app.post("/api/v1/vector-dbs/deploy", response_model=DeploymentResponse)
async def deploy_vector_db(
    request: DeploymentRequest,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """One-click deploy vector DB."""
    result = deployment_service.deploy_vector_db(request.db_type, current_user.id)
    return result

@app.post("/api/v1/vector-dbs/configure", response_model=Dict[str, Any])
async def configure_vector_db(
    config_data: VectorDBConfigCreate,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Configure vector DB connection."""
    # Store config (encrypt sensitive data)
    pass

@app.get("/api/v1/vector-dbs/status")
async def get_vector_db_status(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Get vector DB connection status."""
    # Need embeddings service here
    pass

# ==============================================================================
# DOCUMENT MANAGEMENT
# ==============================================================================

@app.post("/api/v1/documents/upload", response_model=Dict[str, Any])
async def upload_document(
    file: UploadFile = File(...),
    collection_id: Optional[str] = Form(None),
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload document to vector DB."""
    # Process and store
    pass

@app.get("/api/v1/documents", response_model=List[Dict[str, Any]])
async def list_documents(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """List all user documents."""
    pass

@app.delete("/api/v1/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete document."""
    pass

# ==============================================================================
# QUERY ENDPOINTS
# ==============================================================================

# @app.post("/api/v1/query", response_model=QueryResponse)
# async def query(
#     request: QueryRequest,
#     current_user: User = Security(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Execute LangGraph query."""
#     return graph_service.execute_query(db, current_user.id, request)

@app.post("/api/v1/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute LangGraph query."""
    try:
        logger.info(f"Processing query for user: {current_user.email}")
        result = graph_service.execute_query(db, current_user.id, request.dict())
        logger.info(f"Query completed: {result.get('status')}")
        return result
    except Exception as e:
        logger.error(f"Query endpoint error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/api/v1/query/stream")
async def query_stream(
    request: QueryRequest,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Stream LangGraph query response."""
    # Server-Sent Events
    pass

@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation history."""
    pass

@app.delete("/api/v1/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete conversation."""
    pass

# ==============================================================================
# HEALTH & INFO
# ==============================================================================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}

@app.get("/api/v1/info")
async def get_platform_info():
    return {
        "supported_llm_providers": settings.SUPPORTED_LLM_PROVIDERS,
        "supported_vector_dbs": settings.SUPPORTED_VECTOR_DBS,
        "version": "1.0.0"
    }

@app.post("/api/v1/research/start")
async def start_research(
    request: ResearchRequest,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Start an autonomous research agent."""
    
    # Run the AutoResearch Graph
    initial_state = {
        "goal": request.goal,
        "plan": [],
        "current_step": 0,
        "gathered_info": [],
        "draft_report": "",
        "critique": "",
        "iteration_count": 0,
        "finished": False
    }
    
    # Stream the progress to the user
    async def generate():
        for event in auto_research_graph.stream(initial_state):
            yield f" {json.dumps(event)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/webhooks/power-automate/query")
async def power_automate_webhook(request: dict):
    """Endpoint designed for Microsoft Power Automate HTTP Trigger."""
    question = request.get("question")
    # Execute LangGraph
    result = graph_service.execute_query(...)
    return {"answer": result["answer"], "status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)