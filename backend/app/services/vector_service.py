from typing import Optional, Dict, Any, List
from langchain_community.vectorstores import Chroma, Qdrant, Weaviate, Milvus
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from app.models import VectorDBConfig
from app.encryption import encryption_service
from sqlalchemy.orm import Session
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

class VectorService:
    """Dynamic Vector DB provider based on user's configuration."""
    
    def __init__(self):
        self.supported_dbs = ["chroma", "pinecone", "qdrant", "weaviate", "milvus"]
    
    def get_vector_store(
        self, 
        db: Session, 
        user_id: str, 
        embeddings: Embeddings,
        collection_name: Optional[str] = None
    ):
        """
        Get vector store instance based on user's configured DB.
        Supports Chroma (local), Pinecone, Qdrant, Weaviate, Milvus.
        """
        # Get user's vector DB config
        config_record = db.query(VectorDBConfig).filter(
            VectorDBConfig.user_id == user_id,
            VectorDBConfig.is_active == True
        ).first()
        
        if not config_record:
            # Default to local Chroma if no config
            return self._create_chroma_local(user_id, embeddings, collection_name)
        
        db_type = config_record.db_type
        config = config_record.config  # JSON config (may contain encrypted values)
        
        if db_type == "chroma":
            return self._create_chroma_local(user_id, embeddings, collection_name)
        elif db_type == "pinecone":
            return self._create_pinecone(config, embeddings, collection_name)
        elif db_type == "qdrant":
            return self._create_qdrant(config, embeddings, collection_name)
        elif db_type == "weaviate":
            return self._create_weaviate(config, embeddings, collection_name)
        elif db_type == "milvus":
            return self._create_milvus(config, embeddings, collection_name)
        else:
            raise ValueError(f"Unsupported vector DB: {db_type}")
    
    def _create_chroma_local(self, user_id: str, embeddings: Embeddings, collection_name: str = None):
        """Create local Chroma DB (no API key needed)."""
        persist_dir = f"./data/chroma_db/{user_id}"
        os.makedirs(persist_dir, exist_ok=True)
        
        collection = collection_name or "default"
        
        return Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings,
            collection_name=collection
        )
    
    def _create_pinecone(self, config: dict, embeddings: Embeddings, collection_name: str = None):
        """Create Pinecone vector store."""
        api_key = encryption_service.decrypt(config.get("api_key", ""))
        environment = config.get("environment", "us-west1-gcp")
        index_name = config.get("index_name", collection_name or "langgraph-index")
        
        return PineconeVectorStore.from_existing_index(
            embedding=embeddings,
            index_name=index_name,
            api_key=api_key
        )
    
    def _create_qdrant(self, config: dict, embeddings: Embeddings, collection_name: str = None):
        """Create Qdrant vector store."""
        url = config.get("url", "http://localhost:6333")
        api_key = config.get("api_key")
        if api_key:
            api_key = encryption_service.decrypt(api_key)
        
        collection = collection_name or "langgraph_collection"
        
        return Qdrant.from_existing_collection(
            embedding=embeddings,
            url=url,
            collection_name=collection,
            api_key=api_key
        )
    
    def _create_weaviate(self, config: dict, embeddings: Embeddings, collection_name: str = None):
        """Create Weaviate vector store."""
        url = config.get("url", "http://localhost:8080")
        api_key = config.get("api_key")
        if api_key:
            api_key = encryption_service.decrypt(api_key)
        
        collection = collection_name or "LangGraphCollection"
        
        return Weaviate.from_existing_collection(
            embedding=embeddings,
            url=url,
            index_name=collection,
            auth_client_secret=api_key
        )
    
    def _create_milvus(self, config: dict, embeddings: Embeddings, collection_name: str = None):
        """Create Milvus vector store."""
        uri = config.get("uri", "./milvus.db")
        collection = collection_name or "langgraph_collection"
        
        return Milvus.from_existing_collection(
            embedding_function=embeddings,
            connection_args={"uri": uri},
            collection_name=collection
        )
    
    def test_connection(self, db: Session, user_id: str, embeddings: Embeddings) -> Dict[str, Any]:
        """Test vector DB connection."""
        try:
            vector_store = self.get_vector_store(db, user_id, embeddings)
            # Simple test search
            results = vector_store.similarity_search("test", k=1)
            return {
                "success": True,
                "message": "Vector DB connection successful",
                "document_count": len(results)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_deployment_config(self, db_type: str) -> Dict[str, Any]:
        """Get Docker deployment config for vector DB."""
        deployments = {
            "chroma": {
                "name": "Chroma DB (Local)",
                "description": "No deployment needed. Runs locally on your machine.",
                "docker_required": False,
                "setup_steps": ["None - automatic"]
            },
            "pinecone": {
                "name": "Pinecone (Cloud)",
                "description": "Managed vector database. Sign up at pinecone.io",
                "docker_required": False,
                "setup_steps": [
                    "Create account at pinecone.io",
                    "Create new index",
                    "Copy API key and environment",
                    "Enter in configuration panel"
                ]
            },
            "qdrant": {
                "name": "Qdrant (Self-hosted or Cloud)",
                "description": "Open-source vector database",
                "docker_required": True,
                "docker_compose": """
services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_storage:/qdrant/storage
""",
                "setup_steps": [
                    "Run docker-compose up -d",
                    "Access at http://localhost:6333",
                    "Copy URL to configuration panel"
                ]
            },
            "weaviate": {
                "name": "Weaviate (Self-hosted or Cloud)",
                "description": "Open-source vector database",
                "docker_required": True,
                "docker_compose": """
services:
  weaviate:
    image: semitechnologies/weaviate:1.19.0
    ports:
      - "8080:8080"
    environment:
      - QUERY_DEFAULTS_LIMIT=25
      - AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true
    volumes:
      - ./weaviate_/var/lib/weaviate
""",
                "setup_steps": [
                    "Run docker-compose up -d",
                    "Access at http://localhost:8080",
                    "Copy URL to configuration panel"
                ]
            },
            "milvus": {
                "name": "Milvus (Self-hosted)",
                "description": "Cloud-native vector database",
                "docker_required": True,
                "docker_compose": """
# Download from https://github.com/milvus-io/milvus/releases
# Run docker-compose up -d
""",
                "setup_steps": [
                    "Download docker-compose.yml from Milvus docs",
                    "Run docker-compose up -d",
                    "Access at http://localhost:9091",
                    "Copy URI to configuration panel"
                ]
            }
        }
        return deployments.get(db_type, {})

vector_service = VectorService()