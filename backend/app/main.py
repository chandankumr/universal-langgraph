from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import json
import uuid
from datetime import datetime
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
from app.services.document_service import document_service
# from app.graphs import auto_research_graph
# from app.graphs.auto_research_graph import auto_research_graph

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
    key: APIKeyCreate,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Add API key for a provider (encrypted)."""
    from app.models import APIKey
    from app.encryption import encryption_service
    import uuid
    
    # Check if key already exists for this provider
    existing = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.provider == key.provider
    ).first()
    
    if existing:
        # Update existing
        existing.encrypted_key = encryption_service.encrypt(key.api_key)
        existing.is_active = True
        db.commit()
        return {"message": f"API key for {key.provider} updated", "status": "updated"}
    else:
        # Create new
        db_key = APIKey(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            provider=key.provider,
            encrypted_key=encryption_service.encrypt(key.api_key),
            is_active=True
        )
        db.add(db_key)
        db.commit()
        return {"message": f"API key for {key.provider} added", "status": "created"}

@app.get("/api/v1/keys", response_model=List[Dict[str, Any]])
async def list_api_keys(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """List all configured API keys (masked)."""
    from app.models import APIKey
    
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    
    return [
        {
            "id": k.id,
            "provider": k.provider,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat(),
            "last_used": k.last_used.isoformat() if k.last_used else None,
            "key_preview": k.encrypted_key[:10] + "..." if k.encrypted_key else "Not set"
        }
        for k in keys
    ]

@app.delete("/api/v1/keys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete API key."""
    from app.models import APIKey
    
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    db.delete(key)
    db.commit()
    
    return {"message": "API key deleted", "key_id": key_id}


@app.post("/api/v1/keys/test/{provider}")
async def test_api_key(
    provider: str,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Test API key connection."""
    result = llm_service.test_connection(db, current_user.id, provider)
    if result["success"]:
        return {"status": "success", "message": f"{provider} connection OK"}
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Connection failed"))


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
    from app.models import VectorDBConfig
    from app.encryption import encryption_service
    import uuid
    
    # Encrypt sensitive data in config
    encrypted_config = config_data.config.copy()
    if "api_key" in encrypted_config:
        encrypted_config["api_key"] = encryption_service.encrypt(encrypted_config["api_key"])
    
    # Check if config exists
    existing = db.query(VectorDBConfig).filter(
        VectorDBConfig.user_id == current_user.id,
        VectorDBConfig.db_type == config_data.db_type
    ).first()
    
    if existing:
        existing.config = encrypted_config
        existing.collection_name = config_data.collection_name
        db.commit()
        return {"message": "Vector DB configuration updated", "status": "updated"}
    else:
        db_config = VectorDBConfig(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            db_type=config_data.db_type,
            config=encrypted_config,
            collection_name=config_data.collection_name,
            is_active=True
        )
        db.add(db_config)
        db.commit()
        return {"message": "Vector DB configuration saved", "status": "created"}

# @app.get("/api/v1/vector-dbs/status", response_model=Dict[str, Any])
# async def get_vector_db_status(
#     current_user: User = Security(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Get vector DB connection status."""
#     from app.models import VectorDBConfig
    
#     config = db.query(VectorDBConfig).filter(
#         VectorDBConfig.user_id == current_user.id,
#         VectorDBConfig.is_active == True
#     ).first()
    
#     if config:
#         return {
#             "configured": True,
#             "db_type": config.db_type,
#             "collection": config.collection_name,
#             "status": "active"
#         }
#     else:
#         return {
#             "configured": False,
#             "db_type": settings.DEFAULT_VECTOR_DB,
#             "collection": "default",
#             "status": "using defaults"
#         }

@app.get("/api/v1/vector-dbs/status", response_model=Dict[str, Any])
async def get_vector_db_status(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all vector DB connection statuses with actual counts."""
    from app.models import UserPreference
    from app.database import vector_db
    
    pref = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()
    
    current_db = pref.preferred_vector_db if pref else "chroma"
    
    # Get actual document count from ChromaDB
    try:
        vector_count = vector_db.get_collection_count(collection_id="default")
    except:
        vector_count = 0
    
    statuses = {}

    # Check Chroma (Always available)
    statuses["chroma"] = {
        "configured": True,
        "status": "connected",
        "is_active": current_db == "chroma",
        "document_count": vector_count
    }

    for db_type in ["pinecone", "qdrant", "weaviate", "milvus"]:
        try:
            status = vector_db.get_status(db_type)
            statuses[db_type] = {
                "configured": status.get("configured", False),
                "status": status.get("status", "unknown"),
                "is_active": db_type == current_db,
                "document_count": vector_count if db_type == "chroma" else 0
            }
        except:
            statuses[db_type] = {
                "configured": False,
                "status": "not_configured",
                "is_active": db_type == current_db,
                "document_count": 0
            }
    
    return {
        "current_db": current_db,
        "total_vectors": vector_count,
        "databases": statuses
    }

# ==============================================================================
# DOCUMENT MANAGEMENT
# ==============================================================================

@app.post("/api/v1/documents/upload", response_model=Dict[str, Any])
async def upload_document(
    file: UploadFile = File(...),
    collection_id: str = Form("default"),
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload document to vector DB."""
    import tempfile
    from pathlib import Path
    
    # Validate file type
    allowed_types = ["pdf", "txt", "md", "docx"]
    file_ext = file.filename.split(".")[-1].lower()
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(allowed_types)}"
        )
    
    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        result = document_service.upload_document(
            db=db,
            user_id=current_user.id,
            file_path=tmp_path,
            filename=file.filename,
            collection_id=collection_id,
            file_type=file_ext,
            file_size=len(content)
        )
        return result
    finally:
        # Cleanup temp file
        Path(tmp_path).unlink(missing_ok=True)

@app.get("/api/v1/documents", response_model=List[Dict[str, Any]])
async def list_documents(
    collection_id: Optional[str] = None,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """List all user documents."""
    return document_service.list_documents(db, current_user.id, collection_id)

@app.delete("/api/v1/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete document."""
    success = document_service.delete_document(db, current_user.id, doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted", "document_id": doc_id}

@app.get("/api/v1/documents/stats", response_model=Dict[str, Any])
async def get_document_stats(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Get storage statistics."""
    return document_service.get_storage_stats(db, current_user.id)

@app.get("/api/v1/documents/collections", response_model=List[Dict[str, Any]])
async def list_collections(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """List all collections/topics."""
    return document_service.list_collections(db, current_user.id)

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

# @app.post("/api/v1/query/stream")
# async def query_stream(
#     request: QueryRequest,
#     current_user: User = Security(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Stream LangGraph query response."""
#     import json
#     from app.graphs.rag_graph import rag_graph
    
#     thread_id = request.thread_id or str(uuid.uuid4())
#     config = {"configurable": {"thread_id": thread_id}}
    
#     messages = request.conversation_history or []
#     messages.append({"role": "user", "content": request.question})
    
#     inputs = {
#         "messages": messages,
#         "question": request.question,
#         "answer": "",
#         "router_decision": ""
#     }
    
#     async def generate():
#         try:
#             for event in rag_graph.stream(inputs, config):
#                 yield f"data: {json.dumps(event)}\n\n"
            
#             final_state = rag_graph.get_state(config)
#             yield f"data: {json.dumps({'type': 'complete', 'state': final_state.values if final_state else {}})}\n\n"
#         except Exception as e:
#             yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
#     return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/api/v1/conversations/{conversation_id}", response_model=Dict[str, Any])
async def get_conversation(
    conversation_id: str,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation history."""
    from app.models import Conversation, Message
    
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat()
            }
            for m in messages
        ]
    }

@app.delete("/api/v1/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete conversation."""
    from app.models import Conversation
    
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversation deleted", "conversation_id": conversation_id}

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
    """Auto-research agent - Coming Soon"""
    return {
        "status": "info",
        "message": "Auto-research agent is under development. Please use standard query endpoint."
    }

# @app.post("/api/v1/research/start")
# async def start_research(
#     request: ResearchRequest,
#     current_user: User = Security(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Start an autonomous research agent with multi-hop search."""
    
#     # Run the AutoResearch Graph
#     initial_state = {
#         "goal": request.goal,
#         "plan": [],
#         "current_step": 0,
#         "gathered_info": [],
#         "draft_report": "",
#         "critique": "",
#         "iteration_count": 0,
#         "finished": False
#     }
    
#     # Stream the progress to the user
#     async def generate():
#         try:
#             for event in auto_research_graph.stream(initial_state):
#                 yield f"data: {json.dumps(event)}\n\n"
#         except Exception as e:
#             yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
#     return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/webhooks/power-automate/query")
async def power_automate_webhook(request: dict):
    """Endpoint designed for Microsoft Power Automate HTTP Trigger."""
    question = request.get("question")
    # Execute LangGraph
    result = graph_service.execute_query(...)
    return {"answer": result["answer"], "status": "success"}


# ==============================================================================
# DOCUMENT MANAGEMENT ENDPOINTS
# ==============================================================================

@app.post("/api/v1/documents/upload", response_model=Dict[str, Any])
async def upload_document(
    file: UploadFile = File(...),
    collection_id: str = Form("default"),
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a document to the vector database."""
    import tempfile
    from pathlib import Path
    
    # Validate file type
    allowed_types = ["pdf", "txt", "md", "docx"]
    file_ext = file.filename.split(".")[-1].lower()
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(allowed_types)}"
        )
    
    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        result = document_service.upload_document(
            db=db,
            user_id=current_user.id,
            file_path=tmp_path,
            filename=file.filename,
            collection_id=collection_id,
            file_type=file_ext,
            file_size=len(content)
        )
        return result
    finally:
        # Cleanup temp file
        Path(tmp_path).unlink(missing_ok=True)

@app.get("/api/v1/documents", response_model=List[Dict[str, Any]])
async def list_documents(
    collection_id: Optional[str] = None,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """List all user documents."""
    return document_service.list_documents(db, current_user.id, collection_id)

@app.delete("/api/v1/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document."""
    success = document_service.delete_document(db, current_user.id, doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted", "document_id": doc_id}

@app.get("/api/v1/documents/stats", response_model=Dict[str, Any])
async def get_document_stats(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Get storage statistics."""
    return document_service.get_storage_stats(db, current_user.id)

@app.get("/api/v1/documents/collections", response_model=List[Dict[str, Any]])
async def list_collections(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """List all collections/topics."""
    return document_service.list_collections(db, current_user.id)

# ==============================================================================
# MODEL MANAGEMENT ENDPOINTS
# ==============================================================================

@app.get("/api/v1/models", response_model=List[Dict[str, Any]])
async def list_models():
    """List all available LLM models."""
    return [
        {"provider": "ollama", "model": "llama3.1:8b", "type": "local", "free": True},
        {"provider": "ollama", "model": "mistral:7b", "type": "local", "free": True},
        {"provider": "groq", "model": "llama3-8b-8192", "type": "cloud", "free": True},
        {"provider": "groq", "model": "mixtral-8x7b-32768", "type": "cloud", "free": True},
        {"provider": "google", "model": "gemini-1.5-flash", "type": "cloud", "free": True},
        {"provider": "openai", "model": "gpt-4o", "type": "cloud", "free": False},
        {"provider": "openai", "model": "gpt-4o-mini", "type": "cloud", "free": False},
        {"provider": "azure_openai", "model": "gpt-4o", "type": "cloud", "free": False},
    ]

@app.post("/api/v1/models/switch", response_model=Dict[str, Any])
async def switch_model(
    provider: str = Form(...),
    model: str = Form(...),
    api_key: Optional[str] = Form(None),
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Switch to a different LLM model (saved to user preferences)."""
    from app.models import UserPreference
    from app.encryption import encryption_service
    import json
    
    # Get or create user preference
    pref = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()
    
    if not pref:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)
    
    # Update preferences
    pref.preferred_llm_provider = provider
    pref.preferred_llm_model = model
    pref.updated_at = datetime.utcnow()
    
    # Save API key if provided (encrypt it)
    if api_key:
        custom_keys = pref.custom_api_keys or {}
        custom_keys[provider] = encryption_service.encrypt(api_key)
        pref.custom_api_keys = custom_keys
    
    db.commit()
    db.refresh(pref)
    
    logger.info(f"User {current_user.email} switched to {provider}/{model}")
    
    return {
        "message": f"Switched to {provider}/{model}",
        "provider": provider,
        "model": model,
        "status": "success",
        "note": "Model will be used for next query"
    }

@app.get("/api/v1/models/current", response_model=Dict[str, Any])
async def get_current_model(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Get currently active model (from user preferences)."""
    from app.models import UserPreference
    
    pref = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()
    
    if pref:
        return {
            "provider": pref.preferred_llm_provider,
            "model": pref.preferred_llm_model,
            "vector_db": pref.preferred_vector_db,
            "has_api_keys": bool(pref.custom_api_keys)
        }
    else:
        # Default fallback
        return {
            "provider": "ollama",
            "model": settings.OLLAMA_MODEL,
            "vector_db": "chroma",
            "has_api_keys": False
        }

# ==============================================================================
# VECTOR DB INFO ENDPOINT
# ==============================================================================

@app.get("/api/v1/vector-db/info", response_model=Dict[str, Any])
async def get_vector_db_info():
    """Get current vector database information."""
    return {
        "type": settings.DEFAULT_VECTOR_DB,
        # "persist_directory": settings.CHROMA_PERSIST_DIR,
        # "client": chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR),
        "collection": settings.CHROMA_COLLECTION_NAME if hasattr(settings, 'CHROMA_COLLECTION_NAME') else "default"
    }

# ==============================================================================
# ADMIN ENDPOINTS
# ==============================================================================

@app.get("/api/v1/admin/postgres/tables", response_model=List[Dict[str, Any]])
async def list_postgres_tables(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """List all PostgreSQL tables with row counts."""
    from sqlalchemy import text
    
    tables_info = [
        {"name": "users", "description": "User accounts and authentication"},
        {"name": "api_keys", "description": "Encrypted API keys for LLM providers"},
        {"name": "documents", "description": "Document metadata (not embeddings)"},
        {"name": "conversations", "description": "Chat conversation history"},
        {"name": "messages", "description": "Individual chat messages"},
        {"name": "user_preferences", "description": "User LLM and vector DB preferences"},
        {"name": "vector_db_configs", "description": "Vector database configurations"}
    ]
    
    # Get actual row counts
    for table in tables_info:
        try:
            result = db.execute(text(f"SELECT COUNT(*) FROM {table['name']}"))
            table["row_count"] = result.scalar()
        except:
            table["row_count"] = 0
    
    return tables_info

@app.get("/api/v1/admin/system/info", response_model=Dict[str, Any])
async def get_system_info(
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Get system information and health status."""
    import psutil
    from app.config import settings
    
    # Get memory usage
    memory = psutil.virtual_memory()
    
    return {
        "backend": {
            "framework": "FastAPI",
            "python_version": "3.11",
            "langgraph_version": "0.0.40"
        },
        "frontend": {
            "framework": "Next.js",
            "version": "14.2.35"
        },
        "database": {
            "type": "PostgreSQL",
            "version": "15",
            "url": settings.DATABASE_URL.split("@")[1].split("/")[0] if settings.DATABASE_URL else "N/A"
        },
        "vector_db": {
            "current": settings.DEFAULT_VECTOR_DB,
            "supported": settings.SUPPORTED_VECTOR_DBS
        },
        "embeddings": {
            "model": "BAAI/bge-small-en-v1.5",
            "device": "cpu"
        },
        "system": {
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_used_percent": memory.percent,
            "cpu_count": psutil.cpu_count()
        }
    }

@app.post("/api/v1/query/stream")
async def query_stream(
    request: QueryRequest,
    current_user: User = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Stream LangGraph query response using SSE."""
    import json
    from app.models import UserPreference
    from app.encryption import encryption_service
    from app.graphs.rag_graph import rag_graph
    from app.config import settings

    async def event_generator():
        try:
            # 1. Get User Preferences
            pref = db.query(UserPreference).filter(
                UserPreference.user_id == current_user.id
            ).first()
            
            provider = pref.preferred_llm_provider if pref else "groq"
            model = pref.preferred_llm_model if pref else "llama-3.1-8b-instant"
            
            # 2. ✅ DECRYPT API KEY (This was missing!)
            api_key = None
            if pref and pref.custom_api_keys and provider in pref.custom_api_keys:
                try:
                    api_key = encryption_service.decrypt(pref.custom_api_keys[provider])
                    logger.info(f"🔑 [STREAM] Decrypted API key for {provider}")
                except Exception as e:
                    logger.error(f"[STREAM] Failed to decrypt key: {e}")
            
            # Fallback to env
            if not api_key:
                if provider == "groq" and settings.GROQ_API_KEY:
                    api_key = settings.GROQ_API_KEY
                    logger.info("🔑 [STREAM] Using Groq Key from .env")
                elif provider == "openai" and settings.OPENAI_API_KEY:
                    api_key = settings.OPENAI_API_KEY
            
            if not api_key:
                yield f"data: {json.dumps({'error': f'{provider} API Key missing'})}\n\n"
                return

            # 3. Prepare Inputs
            inputs = {
                "messages": [{"role": "user", "content": request.question}], 
                "question": request.question
            }
            
            config = {
                "configurable": {
                    "thread_id": str(uuid.uuid4()), 
                    "llm_provider": provider, 
                    "llm_model": model,
                    "llm_api_key": api_key  # Pass the decrypted key!
                }
            }
            
            # 4. Stream Events
            async for event in rag_graph.astream_events(inputs, config, version="v2"):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield f"data: {json.dumps({'token': content})}\n\n"
                        
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)