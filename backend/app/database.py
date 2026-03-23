from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
from langchain_huggingface import HuggingFaceEmbeddings
import logging
import os

logger = logging.getLogger(__name__)

# ===========================
# DATABASE SETUP
# ===========================

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ===========================
# EMBEDDINGS
# ===========================

def get_embeddings():
    """Get embeddings model (CPU-based)."""
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

# ===========================
# MULTI-VECTOR DATABASE MANAGER
# ===========================

class VectorDatabaseManager:
    """Manages multiple vector database backends."""
    
    def __init__(self):
        self.embeddings = get_embeddings()
        self.current_db_type = "chroma"  # Default
        self.clients = {}
        logger.info("✅ Vector Database Manager initialized")
    
    def get_client(self, db_type: str, collection_id: str = "default"):
        """Get or create vector DB client."""
        cache_key = f"{db_type}:{collection_id}"
        
        if cache_key in self.clients:
            return self.clients[cache_key]
        
        try:
            if db_type == "chroma":
                from langchain_chroma import Chroma
                client = Chroma(
                    persist_directory=settings.CHROMA_PERSIST_DIR,
                    embedding_function=self.embeddings,
                    collection_name=collection_id
                )
            
            elif db_type == "pinecone":
                from langchain_pinecone import PineconeVectorStore
                from pinecone import Pinecone
                if not settings.PINECONE_API_KEY:
                    raise ValueError("Pinecone API Key not set")
                
                pc = Pinecone(api_key=settings.PINECONE_API_KEY)
                # Ensure index exists or create it (simplified for demo)
                # In prod, you might want to check if index exists first
                index = pc.Index(collection_id) 
                
                client = PineconeVectorStore(
                    index=index,
                    embedding=self.embeddings
                )
            
            elif db_type == "qdrant":
                from langchain_community.vectorstores import Qdrant
                if not settings.QDRANT_URL:
                    raise ValueError("Qdrant URL not set")
                    
                client = Qdrant.from_existing_collection(
                    embedding=self.embeddings,
                    url=settings.QDRANT_URL,
                    collection_name=collection_id,
                    api_key=getattr(settings, 'QDRANT_API_KEY', None)
                )
            
            elif db_type == "weaviate":
                from langchain_community.vectorstores import Weaviate
                import weaviate
                if not settings.WEAVIATE_URL:
                    raise ValueError("Weaviate URL not set")

                auth_config = None
                if getattr(settings, 'WEAVIATE_API_KEY', None):
                    auth_config = weaviate.AuthApiKey(api_key=settings.WEAVIATE_API_KEY)
                
                client = Weaviate.from_existing_collection(
                    embedding=self.embeddings,
                    url=settings.WEAVIATE_URL,
                    index_name=collection_id,
                    auth_client_secret=auth_config
                )
            
            elif db_type == "milvus":
                from langchain_community.vectorstores import Milvus
                client = Milvus.from_existing_collection(
                    embedding_function=self.embeddings,
                    connection_args={"uri": getattr(settings, 'MILVUS_URI', "./milvus.db")},
                    collection_name=collection_id
                )
            
            else:
                raise ValueError(f"Unsupported vector DB: {db_type}")
            
            self.clients[cache_key] = client
            logger.info(f"✅ Connected to {db_type}/{collection_id}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to connect to {db_type}: {e}")
            raise

    def add_documents(self, documents, collection_id="default", db_type=None):
        """Add documents to vector store."""
        # Use current_db_type if not specified
        target_db = db_type or self.current_db_type
        
        # Get the client for this DB type
        client = self.get_client(target_db, collection_id)
        
        try:
            # Generate unique IDs
            ids = [f"doc_{i}_{collection_id}" for i in range(len(documents))]
            
            # Add to the specific client
            client.add_documents(documents, ids=ids)
            
            logger.info(f"✅ Added {len(documents)} docs to {target_db}/{collection_id}")
            return ids
            
        except Exception as e:
            logger.error(f"Error adding documents to {target_db}: {e}")
            raise
    
    def search(self, query: str, k: int = 5, collection_id="default", db_type=None):
        """Search vector store."""
        target_db = db_type or self.current_db_type
        client = self.get_client(target_db, collection_id)
        
        try:
            results = client.similarity_search(query, k=k)
            logger.info(f"🔍 Search returned {len(results)} results from {target_db}")
            return results
        except Exception as e:
            logger.error(f"Search error in {target_db}: {e}")
            return []
    
    def delete_documents(self, doc_ids: list, collection_id="default", db_type=None):
        """Delete documents from vector store."""
        target_db = db_type or self.current_db_type
        client = self.get_client(target_db, collection_id)
        
        try:
            client.delete(ids=doc_ids)
            logger.info(f"🗑️ Deleted {len(doc_ids)} docs from {target_db}")
            return len(doc_ids)
        except Exception as e:
            logger.error(f"Delete error in {target_db}: {e}")
            raise
    
    def get_collection_count(self, collection_id="default", db_type=None):
        """Get document count in collection."""
        target_db = db_type or self.current_db_type
        
        try:
            client = self.get_client(target_db, collection_id)
            
            # Chroma specific count method
            if target_db == "chroma":
                # Access the underlying collection object
                if hasattr(client, '_collection'):
                    return client._collection.count()
                elif hasattr(client, 'collection'):
                    return client.collection.count()
            
            # Generic fallback for others (might need adjustment based on lib version)
            # For now, return 0 if count method isn't straightforward
            return 0 
            
        except Exception as e:
            logger.warning(f"Could not get count for {target_db}: {e}")
            return 0
    
    def get_status(self, db_type=None):
        """Get vector DB status."""
        target_db = db_type or self.current_db_type
        
        try:
            # Try to get client to verify connection
            self.get_client(target_db, "default")
            return {
                "type": target_db,
                "status": "connected",
                "configured": True
            }
        except Exception as e:
            return {
                "type": target_db,
                "status": f"error: {str(e)}",
                "configured": False
            }
    
    def set_current_db(self, db_type: str):
        """Set current active vector DB."""
        if db_type in ["chroma", "pinecone", "qdrant", "weaviate", "milvus"]:
            self.current_db_type = db_type
            logger.info(f"🔄 Switched active DB to {db_type}")
            return True
        return False

# Singleton instance
vector_db = VectorDatabaseManager()

# ===========================
# SQLALCHEMY HELPERS
# ===========================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    try:
        from app import models
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection tested successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise

def check_health():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except:
        return False





















# from sqlalchemy import create_engine, text
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from app.config import settings
# from langchain_community.vectorstores import Chroma
# from langchain_huggingface import HuggingFaceEmbeddings
# import logging
# import os

# logger = logging.getLogger(__name__)

# # Create database engine
# engine = create_engine(
#     settings.DATABASE_URL,
#     pool_pre_ping=True,
#     pool_size=10,
#     max_overflow=20,
#     echo=settings.DEBUG  # Show SQL queries in debug mode
# )

# # Create session factory
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # Base class for models
# Base = declarative_base()

# # ===========================
# # EMBEDDINGS (Shared across all vector DBs)
# # ===========================

# def get_embeddings():
#     """Get embeddings model (CPU-based, works with all vector DBs)."""
#     return HuggingFaceEmbeddings(
#         model_name="BAAI/bge-small-en-v1.5",
#         model_kwargs={"device": "cpu"},
#         encode_kwargs={"normalize_embeddings": True}
#     )

# # ===========================
# # MULTI-VECTOR DATABASE MANAGER
# # ===========================

# class VectorDatabaseManager:
#     """Manages multiple vector database backends."""
    
#     def __init__(self):
#         self.embeddings = get_embeddings()
#         self.current_db_type = "chroma"  # Default
#         self.clients = {}
#         logger.info("✅ Vector Database Manager initialized")
    
#     def get_client(self, db_type: str, collection_id: str = "default"):
#         """Get or create vector DB client."""
#         cache_key = f"{db_type}:{collection_id}"
        
#         if cache_key in self.clients:
#             return self.clients[cache_key]
        
#         try:
#             if db_type == "chroma":
#                 from langchain_chroma import Chroma
#                 client = Chroma(
#                     persist_directory=settings.CHROMA_PERSIST_DIR,
#                     embedding_function=self.embeddings,
#                     collection_name=collection_id
#                 )
            
#             elif db_type == "pinecone":
#                 from langchain_pinecone import PineconeVectorStore
#                 import pinecone
#                 from pinecone import Pinecone
#                 pc = Pinecone(api_key=settings.PINECONE_API_KEY)

#                 index = pc.Index(collection_id)

#                 client = PineconeVectorStore(
#                     index=index,
#                     embedding=self.embeddings
#                 )
#                 # Get API key from settings or user preferences
#                 # pinecone.init(api_key=settings.PINECONE_API_KEY, environment=settings.PINECONE_ENVIRONMENT)
#                 # client = PineconeVectorStore.from_existing_index(
#                 #     index_name=collection_id,
#                 #     embedding=self.embeddings
#                 # )
            
#             elif db_type == "qdrant":
#                 from langchain_community.vectorstores import Qdrant
#                 client = Qdrant.from_existing_collection(
#                     embedding=self.embeddings,
#                     url=settings.QDRANT_URL,
#                     collection_name=collection_id,
#                     api_key=settings.QDRANT_API_KEY
#                 )
            
#             elif db_type == "weaviate":
#                 from langchain_community.vectorstores import Weaviate
#                 import weaviate
#                 auth_config = None
#                 if settings.WEAVIATE_API_KEY:
#                     auth_config = weaviate.AuthApiKey(api_key=settings.WEAVIATE_API_KEY)
                
#                 client = Weaviate.from_existing_collection(
#                     embedding=self.embeddings,
#                     url=settings.WEAVIATE_URL,
#                     index_name=collection_id,
#                     auth_client_secret=auth_config
#                 )
            
#             elif db_type == "milvus":
#                 from langchain_community.vectorstores import Milvus
#                 client = Milvus.from_existing_collection(
#                     embedding_function=self.embeddings,
#                     connection_args={"uri": settings.MILVUS_URI or "./milvus.db"},
#                     collection_name=collection_id
#                 )
            
#             else:
#                 raise ValueError(f"Unsupported vector DB: {db_type}")
            
#             self.clients[cache_key] = client
#             logger.info(f"✅ Connected to {db_type}/{collection_id}")
#             return client
            
#         except Exception as e:
#             logger.error(f"Failed to connect to {db_type}: {e}")
#             raise

#     # def add_documents(self, documents, collection_id="default", db_type=None):
#     #     """Add documents to vector store."""
#     #     db_type = db_type or self.current_db_type
#     #     client = self.get_client(db_type, collection_id)
        
#     #     ids = [f"doc_{i}_{collection_id}" for i in range(len(documents))]
#     #     client.add_documents(documents, ids=ids)
        
#     #     logger.info(f"Added {len(documents)} docs to {db_type}/{collection_id}")
#     #     return ids

#     def add_documents(self, documents, collection_id="default"):
#         """Add documents to vector store."""
#         try:
#             # Get or create collection
#             collection = Chroma(
#                 persist_directory=self.persist_dir,
#                 embedding_function=self.embeddings,
#                 collection_name=collection_id
#             )
            
#             # Generate IDs
#             ids = [f"doc_{i}_{collection_id}" for i in range(len(documents))]
            
#             # Add to Chroma
#             collection.add_documents(documents, ids=ids)
            
#             logger.info(f"Added {len(documents)} docs to collection '{collection_id}'")
#             return ids
            
#         except Exception as e:
#             logger.error(f"Error adding documents: {e}")
#             raise
    
#     def search(self, query: str, k: int = 5, collection_id="default", db_type=None):
#         """Search vector store."""
#         db_type = db_type or self.current_db_type
#         client = self.get_client(db_type, collection_id)
        
#         results = client.similarity_search(query, k=k)
#         logger.info(f"Search returned {len(results)} results from {db_type}")
#         return results
    
#     def delete_documents(self, doc_ids: list, collection_id="default", db_type=None):
#         """Delete documents from vector store."""
#         db_type = db_type or self.current_db_type
#         client = self.get_client(db_type, collection_id)
        
#         try:
#             client.delete(ids=doc_ids)
#             logger.info(f"Deleted {len(doc_ids)} docs from {db_type}")
#             return len(doc_ids)
#         except Exception as e:
#             logger.error(f"Delete error: {e}")
#             raise
    
#     def get_status(self, db_type=None):
#         """Get vector DB status."""
#         db_type = db_type or self.current_db_type
        
#         try:
#             client = self.get_client(db_type, "default")
#             return {
#                 "type": db_type,
#                 "status": "connected",
#                 "configured": True
#             }
#         except:
#             return {
#                 "type": db_type,
#                 "status": "not_configured",
#                 "configured": False
#             }
    
#     def set_current_db(self, db_type: str):
#         """Set current active vector DB."""
#         if db_type in ["chroma", "pinecone", "qdrant", "weaviate", "milvus"]:
#             self.current_db_type = db_type
#             logger.info(f"Switched to {db_type}")
#             return True
#         return False

# # Singleton instance
# vector_db = VectorDatabaseManager()

# # Add this class for vector DB compatibility
# # class VectorDatabase:
# #     def __init__(self):
# #         self.persist_dir = settings.CHROMA_PERSIST_DIR
# #         os.makedirs(self.persist_dir, exist_ok=True)
        
# #         # Use local embeddings (no API needed)
# #         self.embeddings = HuggingFaceEmbeddings(
# #             model_name="BAAI/bge-small-en-v1.5",
# #             model_kwargs={"device": "cpu"},
# #             encode_kwargs={"normalize_embeddings": True}
# #         )
        
# #         # Initialize Chroma DB
# #         self.client = Chroma(
# #             persist_directory=self.persist_dir,
# #             embedding_function=self.embeddings,
# #             collection_name="default"
# #         )
        
# #         logger.info(f"✅ Vector DB initialized at {self.persist_dir}")
    
# #     def add_documents(self, documents, collection_id="default"):
# #         """Add documents to vector store."""
# #         try:
# #             # Get or create collection
# #             collection = Chroma(
# #                 persist_directory=self.persist_dir,
# #                 embedding_function=self.embeddings,
# #                 collection_name=collection_id
# #             )
            
# #             # Add documents
# #             ids = [f"doc_{i}_{collection_id}" for i in range(len(documents))]
# #             collection.add_documents(documents, ids=ids)
            
# #             logger.info(f"Added {len(documents)} docs to collection '{collection_id}'")
# #             return ids
            
# #         except Exception as e:
# #             logger.error(f"Error adding documents: {e}")
# #             raise
    
# #     def search(self, query: str, k: int = 5, filter_metadata: dict = None):
# #         """Search vector store."""
# #         try:
# #             # Search default collection (or implement collection routing)
# #             results = self.client.similarity_search(query, k=k)
# #             logger.info(f"Search returned {len(results)} results")
# #             return results
# #         except Exception as e:
# #             logger.error(f"Search error: {e}")
# #             return []
    
# #     def delete_documents(self, doc_ids: list):
# #         """Delete documents from vector store."""
# #         try:
# #             # Note: Chroma deletes by ID, you may need to track chunk IDs
# #             # For now, this is a placeholder
# #             logger.info(f"Delete requested for {len(doc_ids)} documents")
# #             return len(doc_ids)
# #         except Exception as e:
# #             logger.error(f"Delete error: {e}")
# #             raise
    
# #     def get_collection_count(self, collection_id="default"):
# #         """Get document count in collection."""
# #         try:
# #             collection = Chroma(
# #                 persist_directory=self.persist_dir,
# #                 embedding_function=self.embeddings,
# #                 collection_name=collection_id
# #             )
# #             return collection._collection.count()
# #         except:
# #             return 0
# # 
# # Singleton instance
# # vector_db = VectorDatabase()

# def get_db():
#     """
#     Dependency that provides a database session.
#     Usage: db: Session = Depends(get_db)
#     """
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# def init_db():
#     """
#     Initialize database tables.
#     Call this once on startup.
#     """
#     try:
#         # Import all models to ensure they're registered with Base
#         from app import models
        
#         # Create all tables
#         Base.metadata.create_all(bind=engine)
#         logger.info("✅ Database tables created successfully")
        
#         # Test connection
#         db = SessionLocal()
#         # db.execute("SELECT 1")
#         db.execute(text("SELECT 1"))
#         db.close()
#         logger.info("✅ Database connection tested successfully")
        
#     except Exception as e:
#         logger.error(f"❌ Database initialization failed: {str(e)}")
#         raise

# def check_health():
#     """
#     Check if database is healthy.
#     Returns True if connection works, False otherwise.
#     """
#     try:
#         db = SessionLocal()
#         # db.execute("SELECT 1")
#         db.execute(text("SELECT 1"))
#         db.close()
#         return True
#     except Exception as e:
#         logger.error(f"Database health check failed: {str(e)}")
#         return False