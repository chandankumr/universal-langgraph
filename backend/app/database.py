from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
from langchain_huggingface import HuggingFaceEmbeddings
# from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import uuid
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

        # testing for parent-child indexing
        self.parent_store = {}        # parent_id -> parent_doc
        self.child_to_parent = {}    # child_id -> parent_id
        # self.parent_store[parent_id] = parent_doc.page_content
        # ✅ BM25 Cache
        self.bm25_index = None
        self.bm25_docs = []
        self.bm25_collection_id = None
        
        logger.info("✅ Vector Database Manager initialized")

    def _build_bm25_index(self, collection_id="default"):
        """Build BM25 index once (cached)."""
        from rank_bm25 import BM25Okapi
        
        try:
            logger.info("🔨 Building BM25 index...")
            
            # Get all documents ONCE
            all_docs = self.get_all_documents(collection_id)
            
            if not all_docs:
                logger.warning("⚠️ No documents for BM25 index")
                return
            
            # Store documents
            self.bm25_docs = all_docs
            
            # Tokenize once
            tokenized_docs = [doc.lower().split() for doc in all_docs]
            
            # Build index
            self.bm25_index = BM25Okapi(tokenized_docs)
            self.bm25_collection_id = collection_id
            
            logger.info(f"✅ BM25 index built: {len(all_docs)} documents")
            
        except Exception as e:
            logger.error(f"❌ BM25 index build failed: {e}")
            self.bm25_index = None
    
    def bm25_search(self, query: str, k: int = 15):
        """Search using cached BM25 index."""
        if not self.bm25_index or not self.bm25_docs:
            logger.warning("⚠️ BM25 index not built, building now...")
            self._build_bm25_index()
            
            if not self.bm25_index:
                return []
        
        try:
            # Tokenize query
            query_tokens = query.lower().split()
            
            # Get scores (fast - index is pre-built)
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Get top-k
            top_indices = scores.argsort()[-k:][::-1]
            
            results = []
            for i in top_indices:
                if scores[i] > 0:
                    results.append((self.bm25_docs[i], float(scores[i])))
            
            return results
            
        except Exception as e:
            logger.error(f"❌ BM25 search error: {e}")
            return []
    
    def invalidate_bm25_cache(self):
        """Clear BM25 cache (call after document upload/delete)."""
        self.bm25_index = None
        self.bm25_docs = []
        self.bm25_collection_id = None
        logger.info("🗑️ BM25 cache invalidated")
    
    def retrieve_parent_documents(self, query, collection_id="default", k=5):
        """Retrieve parent documents via child similarity search."""

        vectorstore = self.get_client("chroma", collection_id)

        # 1. Search child chunks
        child_results = vectorstore.similarity_search(query, k=k)

        # 2. Map to parents
        parent_ids = set()
        parent_docs = []

        for child in child_results:
            parent_id = child.metadata.get("parent_id")

            if parent_id and parent_id not in parent_ids:
                parent_ids.add(parent_id)
                parent_docs.append(self.parent_store[parent_id])

        return parent_docs

    def add_documents_parent_child(self, documents, collection_id="default"):
        """Custom Parent-Child indexing with BATCHED inserts (FIXED)."""
        
        try:
            from app.database import SessionLocal
            from app.models import ParentDocument
            
            # -------------------------------
            # Splitters
            # -------------------------------
            parent_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=200
            )

            child_splitter = RecursiveCharacterTextSplitter(
                chunk_size=400,
                chunk_overlap=50
            )

            parent_docs = parent_splitter.split_documents(documents)
            all_child_docs = []

            db = SessionLocal()
            
            try:
                # -------------------------------
                # Create parent + child mapping
                # -------------------------------
                for parent_doc in parent_docs:
                    parent_id = str(uuid.uuid4())
                    
                    # ✅ SAVE TO SQL
                    parent_record = ParentDocument(
                        id=parent_id,
                        collection_id=collection_id,
                        content=parent_doc.page_content,
                        doc_metadata=parent_doc.metadata
                    )
                    db.add(parent_record)
                    
                    child_docs = child_splitter.split_documents([parent_doc])

                    for child_doc in child_docs:
                        child_id = str(uuid.uuid4())
                        child_doc.metadata["parent_id"] = parent_id
                        child_doc.metadata["child_id"] = child_id
                        all_child_docs.append(child_doc)

                db.commit()
                
                # -------------------------------
                # ✅ BATCHED: Store child docs in vector DB (FIXED)
                # -------------------------------
                vectorstore = self.get_client("chroma", collection_id)
                
                # ChromaDB 1.5+ has max batch size of 5461
                # Split into batches of 5000 to be safe
                BATCH_SIZE = 5000
                total_added = 0
                
                for i in range(0, len(all_child_docs), BATCH_SIZE):
                    batch = all_child_docs[i:i + BATCH_SIZE]
                    vectorstore.add_documents(batch)
                    total_added += len(batch)
                    logger.info(f"✅ Added batch {i//BATCH_SIZE + 1}: {len(batch)} chunks (Total: {total_added}/{len(all_child_docs)})")

                logger.info(f"✅ Parent-Child Indexing Done: {len(parent_docs)} parents, {len(all_child_docs)} children in {total_added//BATCH_SIZE + 1} batches")
                return list(self.parent_store.keys()) if hasattr(self, 'parent_store') else ["sql_persisted"]
                
            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Parent-Child failed: {e}")
            # ✅ FIX: Raise a proper exception, not a list
            raise Exception(f"Parent-Child indexing failed: {str(e)}")

    def get_client(self, db_type: str, collection_id: str = "default"):
        """Get or create vector DB client."""
        cache_key = f"{db_type}:{collection_id}"
        
        if cache_key in self.clients:
            return self.clients[cache_key]
        
        try:
            
            if db_type == "chroma":
                from langchain_chroma import Chroma
                import chromadb
                
                # ✅ FIX FOR CHROMADB 1.5+
                # 1. Create the PersistentClient explicitly
                # persist_dir = settings.CHROMA_PERSIST_DIR
                persist_dir = settings.CHROMA_PERSIST_DIR or os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chroma_db"
                )

                # ✅ Use HttpClient-style init compatible with chromadb 1.5.x
                chroma_client = chromadb.PersistentClient(path=persist_dir)

                # ✅ Get or create the collection first explicitly
                collection = chroma_client.get_or_create_collection(name=collection_id)

                # ✅ Pass collection directly — avoids internal Settings lookup
                client = Chroma(
                    client=chroma_client,
                    collection_name=collection_id,
                    embedding_function=self.embeddings,
                    collection_metadata={"hnsw:space": "cosine"}
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

        # Use Parent-Child for Chroma (best for context retrieval)
        if target_db == "chroma":
            return self.add_documents_parent_child(documents, collection_id)
        
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
        """Search returning FULL parent documents from SQL (FIXED)."""
        
        try:
            from app.database import SessionLocal
            from app.models import ParentDocument
            
            vectorstore = self.get_client("chroma", collection_id)

            # Step 1: search child chunks
            child_results = vectorstore.similarity_search(query, k=k)

            # Step 2: map to parent docs from SQL
            parent_ids = set()
            for child in child_results:
                parent_id = child.metadata.get("parent_id")
                if parent_id:
                    parent_ids.add(parent_id)

            # Step 3: Fetch parent content from PostgreSQL
            db = SessionLocal()
            try:
                parent_records = db.query(ParentDocument).filter(
                    ParentDocument.id.in_(parent_ids),
                    ParentDocument.collection_id == collection_id
                ).all()
                
                # parent_docs = [Document(page_content=p.content, metadata=p.metadata or {}) 
                #             for p in parent_records]

                # Fetch from SQL
                parent_docs = [Document(page_content=p.content, metadata=p.doc_metadata or {}) 
                            for p in parent_records]
                
                logger.info(f"🔍 Returned {len(parent_docs)} parent docs from SQL")
                return parent_docs
                
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Search error: {e}")
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
    
    def search_with_rerank(self, query: str, k: int = 15, collection_id="default", db_type=None):
        """Search with Hybrid Search + Re-Ranking for better precision."""
        # ✅ CORRECT IMPORTS FOR LANGCHAIN 0.1+
        from langchain_classic.retrievers import ContextualCompressionRetriever
        # from langchain_community.document_compressors import CrossEncoderReranker
        from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
        from langchain_community.cross_encoders import HuggingFaceCrossEncoder
        
        target_db = db_type or self.current_db_type
        client = self.get_client(target_db, collection_id)

        if not client:
            return self.search(query, k, collection_id, db_type)
        
        try:
            # Step 1: Get more candidates initially (cast wider net)
            # We fetch 3x the desired amount to give the reranker enough options
            initial_k = k * 3
            base_retriever = client.as_retriever(search_kwargs={"k": min(initial_k, 50)})
            
            # Step 2: Initialize the Cross-Encoder Reranker
            # This model is small, fast, and runs locally on CPU
            # model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
            model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            logger.info(f"Loading lightweight reranker: {model_name}...")
            model = HuggingFaceCrossEncoder(model_name=model_name)
            compressor = CrossEncoderReranker(model=model, top_n=k)
            
            # Step 3: Wrap the retriever with the compressor
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=base_retriever
            )
            
            # Step 4: Execute search (this triggers the reranking internally)
            # Note: In newer LangChain, we use invoke or get_relevant_documents
            reranked_results = compression_retriever.invoke(query)
            
            logger.info(f"🔍 Hybrid Search: Retrieved {len(reranked_results)} docs (after re-rank)")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            # Fallback to regular vector search if reranking fails
            return self.search(query, k, collection_id, db_type)

    def get_azure_client(self, collection_id: str = "default"):
        """Get Azure AI Search client."""
        from langchain_community.vectorstores import AzureSearch
        from app.config import settings
        
        try:
            vector_store = AzureSearch(
                azure_search_endpoint=settings.AZURE_SEARCH_ENDPOINT,
                azure_search_key=settings.AZURE_SEARCH_KEY,
                index_name=settings.AZURE_SEARCH_INDEX_NAME,
                embedding_function=self.embeddings,
            )
            return vector_store
        except Exception as e:
            logger.error(f"Azure Search connection failed: {e}")
            return None
        
    def get_all_documents(self, collection_id="default", db_type=None):
        """Get all documents from vector store for BM25 search."""
        target_db = db_type or self.current_db_type
        client = self.get_client(target_db, collection_id)
        
        try:
            # Get all documents from ChromaDB
            results = client.get(include=["documents"])
            return results.get("documents", [])
        except Exception as e:
            logger.error(f"Error getting all documents: {e}")
            return []

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
# from langchain_huggingface import HuggingFaceEmbeddings
# import logging
# import os

# logger = logging.getLogger(__name__)

# # ===========================
# # DATABASE SETUP
# # ===========================

# engine = create_engine(
#     settings.DATABASE_URL,
#     pool_pre_ping=True,
#     pool_size=10,
#     max_overflow=20,
#     echo=settings.DEBUG
# )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# # ===========================
# # EMBEDDINGS
# # ===========================

# def get_embeddings():
#     """Get embeddings model (CPU-based)."""
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

#     def add_documents_parent_child(self, documents, collection_id="default"):
#         """Add documents with Parent-Child indexing for better context retrieval."""
#         # from langchain.retrievers import ParentDocumentRetriever
#         try:
#             from langchain.retrievers import ParentDocumentRetriever
#         except ImportError:
#             from langchain_community.retrievers import ParentDocumentRetriever
#         # from langchain_community.retrievers import ParentDocumentRetriever
#         from langchain.storage import InMemoryStore
#         from langchain.text_splitter import RecursiveCharacterTextSplitter
#         from langchain_chroma import Chroma
        
#         try:
#             # Parent splitter (large chunks for context)
#             parent_splitter = RecursiveCharacterTextSplitter(
#                 chunk_size=2000,
#                 chunk_overlap=200
#             )
            
#             # Child splitter (small chunks for search)
#             child_splitter = RecursiveCharacterTextSplitter(
#                 chunk_size=400,
#                 chunk_overlap=50
#             )
            
#             # Create parent documents
#             parent_docs = parent_splitter.split_documents(documents)
            
#             # Create store for parent documents
#             parent_store = InMemoryStore()
            
#             # Get Chroma client
#             chroma_client = self.get_client("chroma", collection_id)
            
#             # Create retriever
#             retriever = ParentDocumentRetriever(
#                 vectorstore=chroma_client,
#                 docstore=parent_store,
#                 child_splitter=child_splitter,
#                 parent_splitter=parent_splitter,
#             )
            
#             # Add documents
#             retriever.add_documents(parent_docs)
            
#             logger.info(f"✅ Added {len(parent_docs)} parent docs with Parent-Child indexing")
#             return [f"parent_{i}" for i in range(len(parent_docs))]
            
#         except ImportError as ie:
#             logger.error(f"Import error for Parent-Child: {ie}. Falling back to standard add.")
#             # Fallback to regular add if imports fail
#             return self.add_documents(documents, collection_id)
#         except Exception as e:
#             logger.error(f"Error in Parent-Child indexing: {e}")
#             # Fallback to regular add
#             return self.add_documents(documents, collection_id)
    
#     def get_client(self, db_type: str, collection_id: str = "default"):
#         """Get or create vector DB client."""
#         cache_key = f"{db_type}:{collection_id}"
        
#         if cache_key in self.clients:
#             return self.clients[cache_key]
        
#         try:
#             # if db_type == "chroma":
#             #     from langchain_chroma import Chroma
#             #     client = Chroma(
#             #         persist_directory=settings.CHROMA_PERSIST_DIR,
#             #         embedding_function=self.embeddings,
#             #         collection_name=collection_id
#             #     )
            
#             if db_type == "chroma":
#                 from langchain_chroma import Chroma
#                 import chromadb
                
#                 # ✅ FIX FOR CHROMADB 1.5+
#                 # 1. Create the PersistentClient explicitly
#                 # persist_dir = settings.CHROMA_PERSIST_DIR
#                 persist_dir = settings.CHROMA_PERSIST_DIR or os.path.join(
#                     os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chroma_db"
#                 )

#                 # ✅ Use HttpClient-style init compatible with chromadb 1.5.x
#                 chroma_client = chromadb.PersistentClient(path=persist_dir)

#                 # ✅ Get or create the collection first explicitly
#                 collection = chroma_client.get_or_create_collection(name=collection_id)

#                 # ✅ Pass collection directly — avoids internal Settings lookup
#                 client = Chroma(
#                     client=chroma_client,
#                     collection_name=collection_id,
#                     embedding_function=self.embeddings,
#                     collection_metadata={"hnsw:space": "cosine"}
#                 )

#             elif db_type == "pinecone":
#                 from langchain_pinecone import PineconeVectorStore
#                 from pinecone import Pinecone
#                 if not settings.PINECONE_API_KEY:
#                     raise ValueError("Pinecone API Key not set")
                
#                 pc = Pinecone(api_key=settings.PINECONE_API_KEY)
#                 # Ensure index exists or create it (simplified for demo)
#                 # In prod, you might want to check if index exists first
#                 index = pc.Index(collection_id) 
                
#                 client = PineconeVectorStore(
#                     index=index,
#                     embedding=self.embeddings
#                 )
            
#             elif db_type == "qdrant":
#                 from langchain_community.vectorstores import Qdrant
#                 if not settings.QDRANT_URL:
#                     raise ValueError("Qdrant URL not set")
                    
#                 client = Qdrant.from_existing_collection(
#                     embedding=self.embeddings,
#                     url=settings.QDRANT_URL,
#                     collection_name=collection_id,
#                     api_key=getattr(settings, 'QDRANT_API_KEY', None)
#                 )
            
#             elif db_type == "weaviate":
#                 from langchain_community.vectorstores import Weaviate
#                 import weaviate
#                 if not settings.WEAVIATE_URL:
#                     raise ValueError("Weaviate URL not set")

#                 auth_config = None
#                 if getattr(settings, 'WEAVIATE_API_KEY', None):
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
#                     connection_args={"uri": getattr(settings, 'MILVUS_URI', "./milvus.db")},
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

#     def add_documents(self, documents, collection_id="default", db_type=None):
#         """Add documents to vector store."""
#         # Use current_db_type if not specified
#         target_db = db_type or self.current_db_type

#         # Use Parent-Child for Chroma (best for context retrieval)
#         if target_db == "chroma":
#             return self.add_documents_parent_child(documents, collection_id)
        
#         # Get the client for this DB type
#         client = self.get_client(target_db, collection_id)
        
#         try:
#             # Generate unique IDs
#             ids = [f"doc_{i}_{collection_id}" for i in range(len(documents))]
            
#             # Add to the specific client
#             client.add_documents(documents, ids=ids)
            
#             logger.info(f"✅ Added {len(documents)} docs to {target_db}/{collection_id}")
#             return ids
            
#         except Exception as e:
#             logger.error(f"Error adding documents to {target_db}: {e}")
#             raise
    
#     def search(self, query: str, k: int = 5, collection_id="default", db_type=None):
#         """Search vector store."""
#         target_db = db_type or self.current_db_type
#         client = self.get_client(target_db, collection_id)
        
#         try:
#             results = client.similarity_search(query, k=k)
#             logger.info(f"🔍 Search returned {len(results)} results from {target_db}")
#             return results
#         except Exception as e:
#             logger.error(f"Search error in {target_db}: {e}")
#             return []
    
#     def delete_documents(self, doc_ids: list, collection_id="default", db_type=None):
#         """Delete documents from vector store."""
#         target_db = db_type or self.current_db_type
#         client = self.get_client(target_db, collection_id)
        
#         try:
#             client.delete(ids=doc_ids)
#             logger.info(f"🗑️ Deleted {len(doc_ids)} docs from {target_db}")
#             return len(doc_ids)
#         except Exception as e:
#             logger.error(f"Delete error in {target_db}: {e}")
#             raise
    
#     def get_collection_count(self, collection_id="default", db_type=None):
#         """Get document count in collection."""
#         target_db = db_type or self.current_db_type
        
#         try:
#             client = self.get_client(target_db, collection_id)
            
#             # Chroma specific count method
#             if target_db == "chroma":
#                 # Access the underlying collection object
#                 if hasattr(client, '_collection'):
#                     return client._collection.count()
#                 elif hasattr(client, 'collection'):
#                     return client.collection.count()
            
#             # Generic fallback for others (might need adjustment based on lib version)
#             # For now, return 0 if count method isn't straightforward
#             return 0 
            
#         except Exception as e:
#             logger.warning(f"Could not get count for {target_db}: {e}")
#             return 0
    
#     def get_status(self, db_type=None):
#         """Get vector DB status."""
#         target_db = db_type or self.current_db_type
        
#         try:
#             # Try to get client to verify connection
#             self.get_client(target_db, "default")
#             return {
#                 "type": target_db,
#                 "status": "connected",
#                 "configured": True
#             }
#         except Exception as e:
#             return {
#                 "type": target_db,
#                 "status": f"error: {str(e)}",
#                 "configured": False
#             }
    
#     def set_current_db(self, db_type: str):
#         """Set current active vector DB."""
#         if db_type in ["chroma", "pinecone", "qdrant", "weaviate", "milvus"]:
#             self.current_db_type = db_type
#             logger.info(f"🔄 Switched active DB to {db_type}")
#             return True
#         return False
    
#     def search_with_rerank(self, query: str, k: int = 15, collection_id="default", db_type=None):
#         """Search with Hybrid Search + Re-Ranking for better precision."""
#         # ✅ CORRECT IMPORTS FOR LANGCHAIN 0.1+
#         from langchain_classic.retrievers import ContextualCompressionRetriever
#         # from langchain_community.document_compressors import CrossEncoderReranker
#         from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
#         from langchain_community.cross_encoders import HuggingFaceCrossEncoder
        
#         target_db = db_type or self.current_db_type
#         client = self.get_client(target_db, collection_id)

#         if not client:
#             return self.search(query, k, collection_id, db_type)
        
#         try:
#             # Step 1: Get more candidates initially (cast wider net)
#             # We fetch 3x the desired amount to give the reranker enough options
#             initial_k = k * 3
#             base_retriever = client.as_retriever(search_kwargs={"k": min(initial_k, 50)})
            
#             # Step 2: Initialize the Cross-Encoder Reranker
#             # This model is small, fast, and runs locally on CPU
#             # model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
#             model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
#             logger.info(f"Loading lightweight reranker: {model_name}...")
#             model = HuggingFaceCrossEncoder(model_name=model_name)
#             compressor = CrossEncoderReranker(model=model, top_n=k)
            
#             # Step 3: Wrap the retriever with the compressor
#             compression_retriever = ContextualCompressionRetriever(
#                 base_compressor=compressor,
#                 base_retriever=base_retriever
#             )
            
#             # Step 4: Execute search (this triggers the reranking internally)
#             # Note: In newer LangChain, we use invoke or get_relevant_documents
#             reranked_results = compression_retriever.invoke(query)
            
#             logger.info(f"🔍 Hybrid Search: Retrieved {len(reranked_results)} docs (after re-rank)")
#             return reranked_results
            
#         except Exception as e:
#             logger.error(f"Hybrid search error: {e}")
#             # Fallback to regular vector search if reranking fails
#             return self.search(query, k, collection_id, db_type)

#     def get_azure_client(self, collection_id: str = "default"):
#         """Get Azure AI Search client."""
#         from langchain_community.vectorstores import AzureSearch
#         from app.config import settings
        
#         try:
#             vector_store = AzureSearch(
#                 azure_search_endpoint=settings.AZURE_SEARCH_ENDPOINT,
#                 azure_search_key=settings.AZURE_SEARCH_KEY,
#                 index_name=settings.AZURE_SEARCH_INDEX_NAME,
#                 embedding_function=self.embeddings,
#             )
#             return vector_store
#         except Exception as e:
#             logger.error(f"Azure Search connection failed: {e}")
#             return None
        
#     def get_all_documents(self, collection_id="default", db_type=None):
#         """Get all documents from vector store for BM25 search."""
#         target_db = db_type or self.current_db_type
#         client = self.get_client(target_db, collection_id)
        
#         try:
#             # Get all documents from ChromaDB
#             results = client.get(include=["documents"])
#             return results.get("documents", [])
#         except Exception as e:
#             logger.error(f"Error getting all documents: {e}")
#             return []

# # Singleton instance
# vector_db = VectorDatabaseManager()

# # ===========================
# # SQLALCHEMY HELPERS
# # ===========================

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# def init_db():
#     try:
#         from app import models
#         Base.metadata.create_all(bind=engine)
#         logger.info("✅ Database tables created successfully")
        
#         db = SessionLocal()
#         db.execute(text("SELECT 1"))
#         db.close()
#         logger.info("✅ Database connection tested successfully")
#     except Exception as e:
#         logger.error(f"❌ Database initialization failed: {str(e)}")
#         raise

# def check_health():
#     try:
#         db = SessionLocal()
#         db.execute(text("SELECT 1"))
#         db.close()
#         return True
#     except:
#         return False










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