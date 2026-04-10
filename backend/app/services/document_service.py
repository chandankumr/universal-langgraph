from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.database import vector_db  
from app.models import Document as DocumentModel
from app.config import settings
import logging
import uuid
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def upload_document(
        self,
        db: Session,
        user_id: str,
        file_path: str,
        filename: str,
        collection_id: str,
        file_type: str,
        file_size: int
    ) -> Dict[str, Any]:
        """Upload and process a document."""
        
        try:
            # 1. Load document from file
            logger.info(f"Loading file: {file_path}")
            documents = self._load_file(file_path, file_type)
            
            if not documents:
                raise ValueError("No content extracted from file")
            
            # 2. Add metadata
            for doc in documents:
                doc.metadata.update({
                    "collection_id": collection_id,
                    "user_id": user_id,
                    "filename": filename,
                    "file_type": file_type
                })
            
            # 3. Split into chunks
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"Split document into {len(chunks)} chunks")
            
            if not chunks:
                raise ValueError("No chunks created after splitting")
            
            # 4. CRITICAL: Add chunks to Vector DB (Chroma)
            logger.info(f"Adding {len(chunks)} chunks to Vector DB (Collection: {collection_id}) with Parent-Child indexing...")
            try:
                doc_ids = vector_db.add_documents(
                    documents=chunks,
                    collection_id=collection_id
                )
                logger.info(f"✅ SUCCESS: Added {len(doc_ids)} chunks to Vector DB")

                # Invalidate BM25 cache so it rebuilds on next query
                vector_db.invalidate_bm25_cache()
            except Exception as ve:
                logger.error(f"❌ Vector DB Error: {str(ve)}")
                raise ve
            
            # 5. Save metadata to PostgreSQL
            db_doc = DocumentModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                collection_id=collection_id,
                chunk_count=len(chunks),
                status="ready"
            )
            db.add(db_doc)
            db.commit()
            db.refresh(db_doc)
            
            logger.info(f"✅ Upload Complete: {filename} ({len(chunks)} chunks)")
            
            return {
                "document_id": db_doc.id,
                "filename": filename,
                "chunk_count": len(chunks),
                "status": "ready",
                "collection_id": collection_id
            }
            
        except Exception as e:
            logger.error(f"❌ Upload Failed: {str(e)}")
            db.rollback()
            raise
    
    def _load_file(self, file_path: str, file_type: str):
        """Load file based on type."""
        from langchain_community.document_loaders import (
            TextLoader, PyPDFLoader, UnstructuredMarkdownLoader, Docx2txtLoader
        )
        
        try:
            if file_type == "pdf":
                loader = PyPDFLoader(file_path)
                documents = loader.load()
                # Filter out blank or near-blank pages (less than 50 characters)
                documents = [doc for doc in documents if len(doc.page_content.strip()) > 50]
                logger.info(f"Filtered to {len(documents)} non-blank pages")
                return documents
            elif file_type == "md":
                loader = UnstructuredMarkdownLoader(file_path)
            elif file_type == "docx":
                loader = Docx2txtLoader(file_path)
            else:  # txt
                loader = TextLoader(file_path, encoding="utf-8")
            
            return loader.load()
        except Exception as e:
            logger.error(f"File load error: {str(e)}")
            raise
    
    def list_documents(self, db: Session, user_id: str, collection_id: Optional[str] = None) -> List[Dict]:
        query = db.query(DocumentModel).filter(DocumentModel.user_id == user_id)
        if collection_id:
            query = query.filter(DocumentModel.collection_id == collection_id)
        
        docs = query.order_by(DocumentModel.created_at.desc()).all()
        
        return [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "chunk_count": doc.chunk_count,
                "collection_id": doc.collection_id,
                "status": doc.status,
                "created_at": doc.created_at.isoformat()
            }
            for doc in docs
        ]
    
    def delete_document(self, db: Session, user_id: str, doc_id: str) -> bool:
        doc = db.query(DocumentModel).filter(
            DocumentModel.id == doc_id,
            DocumentModel.user_id == user_id
        ).first()
        
        if not doc:
            return False
        
        # Delete from Vector DB
        try:
            vector_db.delete_documents([doc.id], collection_id=doc.collection_id)
            # Invalidate BM25 cache
            vector_db.invalidate_bm25_cache() 
        except Exception as e:
            logger.error(f"Vector DB delete error: {e}")
        
        # Delete from PostgreSQL
        db.delete(doc)
        db.commit()
        return True
    
    def get_storage_stats(self, db: Session, user_id: str) -> Dict[str, Any]:
        docs = db.query(DocumentModel).filter(DocumentModel.user_id == user_id).all()
        
        total_size = sum(doc.file_size for doc in docs)
        total_chunks = sum(doc.chunk_count for doc in docs)
        
        # Get actual vector count
        try:
            vector_count = vector_db.get_collection_count(collection_id="default")
        except:
            vector_count = 0
        
        return {
            "total_documents": len(docs),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_chunks": total_chunks,
            "vector_count": vector_count,
            "limit_mb": 100,
            "usage_percent": round((total_size / (1024 * 1024)) / 100 * 100, 2)
        }
    
    def list_collections(self, db: Session, user_id: str) -> List[Dict]:
        docs = db.query(DocumentModel).filter(DocumentModel.user_id == user_id).all()
        collections = {}
        for doc in docs:
            cid = doc.collection_id
            if cid not in collections:
                collections[cid] = {"collection_id": cid, "document_count": 0, "total_chunks": 0}
            collections[cid]["document_count"] += 1
            collections[cid]["total_chunks"] += doc.chunk_count
        return list(collections.values())

document_service = DocumentService()



















# from typing import List, Optional, Dict, Any
# from sqlalchemy.orm import Session
# from langchain_core.documents import Document
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from app.database import vector_db
# from app.models import Document as DocumentModel
# from app.config import settings
# import logging
# import uuid
# from pathlib import Path
# import os

# logger = logging.getLogger(__name__)

# class DocumentService:
#     def __init__(self):
#         self.text_splitter = RecursiveCharacterTextSplitter(
#             chunk_size=1000,
#             chunk_overlap=200,
#             length_function=len,
#         )
    
#     def upload_document(
#         self,
#         db: Session,
#         user_id: str,
#         file_path: str,
#         filename: str,
#         collection_id: str,
#         file_type: str,
#         file_size: int
#     ) -> Dict[str, Any]:
#         """Upload and process a document."""
        
#         try:
#             # Load document based on type
#             documents = self._load_file(file_path, file_type)
            
#             # Add metadata
#             for doc in documents:
#                 doc.metadata.update({
#                     "collection_id": collection_id,
#                     "user_id": user_id,
#                     "filename": filename,
#                     "file_type": file_type
#                 })
            
#             # Split into chunks
#             chunks = self.text_splitter.split_documents(documents)
#             logger.info(f"Split into {len(chunks)} chunks")
            
#             # Store in vector DB
#             # doc_ids = vector_db.add_documents(chunks, collection_id=collection_id)
#             try:
#                 doc_ids = vector_db.add_documents(
#                     documents=chunks,
#                     collection_id=collection_id
#                 )
#                 logger.info(f"✅ Added {len(doc_ids)} chunks to Vector DB")
#             except Exception as e:
#                 logger.error(f"❌ Vector DB error: {str(e)}")
#                 raise
            
#             # Save to database
#             db_doc = DocumentModel(
#                 id=str(uuid.uuid4()),
#                 user_id=user_id,
#                 filename=filename,
#                 file_path=file_path,
#                 file_size=file_size,
#                 file_type=file_type,
#                 collection_id=collection_id,
#                 chunk_count=len(chunks),
#                 status="ready"
#             )
#             db.add(db_doc)
#             db.commit()
#             db.refresh(db_doc)
            
#             logger.info(f"Uploaded {filename}: {len(chunks)} chunks")
            
#             return {
#                 "document_id": db_doc.id,
#                 "filename": filename,
#                 "chunk_count": len(chunks),
#                 "status": "ready",
#                 "collection_id": collection_id
#             }
            
#         except Exception as e:
#             logger.error(f"❌ Upload error: {str(e)}")
#             db.rollback()
#             raise
    
#     def _load_file(self, file_path: str, file_type: str):
#         """Load file based on type."""
#         from langchain_community.document_loaders import (
#             TextLoader, PyPDFLoader, UnstructuredMarkdownLoader, Docx2txtLoader
#         )
#         try:
#             if file_type == "pdf":
#                 loader = PyPDFLoader(file_path)
#             elif file_type == "md":
#                 loader = UnstructuredMarkdownLoader(file_path)
#             elif file_type == "docx":
#                 loader = Docx2txtLoader(file_path)
#             else:  # txt
#                 loader = TextLoader(file_path, encoding="utf-8")
            
#             return loader.load()
#         except Exception as e:
#             logger.error(f"File load error: {str(e)}")
#             raise
    
#     def list_documents(self, db: Session, user_id: str, collection_id: Optional[str] = None) -> List[Dict]:
#         """List all documents for a user."""
#         query = db.query(DocumentModel).filter(DocumentModel.user_id == user_id)
        
#         if collection_id:
#             query = query.filter(DocumentModel.collection_id == collection_id)
        
#         docs = query.order_by(DocumentModel.created_at.desc()).all()
        
#         return [
#             {
#                 "id": doc.id,
#                 "filename": doc.filename,
#                 "file_type": doc.file_type,
#                 "file_size": doc.file_size,
#                 "chunk_count": doc.chunk_count,
#                 "collection_id": doc.collection_id,
#                 "status": doc.status,
#                 "created_at": doc.created_at.isoformat()
#             }
#             for doc in docs
#         ]
    
#     def delete_document(self, db: Session, user_id: str, doc_id: str) -> bool:
#         """Delete a document."""
#         doc = db.query(DocumentModel).filter(
#             DocumentModel.id == doc_id,
#             DocumentModel.user_id == user_id
#         ).first()
        
#         if not doc:
#             return False
        
#         # Delete from vector DB
#         # vector_db.delete_documents([doc_id])
#         try:
#             vector_db.delete_documents([doc.id], collection_id=doc.collection_id)
#         except Exception as e:
#             logger.error(f"Vector DB delete error: {e}")
        
#         # Delete from database
#         db.delete(doc)
#         db.commit()
        
#         return True
    
#     def get_storage_stats(self, db: Session, user_id: str) -> Dict[str, Any]:
#         """Get storage usage statistics."""
#         docs = db.query(DocumentModel).filter(DocumentModel.user_id == user_id).all()
        
#         total_size = sum(doc.file_size for doc in docs)
#         total_chunks = sum(doc.chunk_count for doc in docs)

#         # Get actual vector count from ChromaDB
#         try:
#             vector_count = vector_db.get_collection_count(collection_id="default")
#         except:
#             vector_count = total_chunks
        
#         return {
#             "total_documents": len(docs),
#             "total_size_bytes": total_size,
#             "total_size_mb": round(total_size / (1024 * 1024), 2),
#             "total_chunks": total_chunks,
#             "vector_count": vector_count,
#             "limit_mb": 100,  # Can be configured
#             "usage_percent": round((total_size / (1024 * 1024)) / 100 * 100, 2)
#         }
    
#     def list_collections(self, db: Session, user_id: str) -> List[Dict]:
#         """List all collections/topics for a user."""
#         docs = db.query(DocumentModel).filter(DocumentModel.user_id == user_id).all()
        
#         collections = {}
#         for doc in docs:
#             cid = doc.collection_id
#             if cid not in collections:
#                 collections[cid] = {
#                     "collection_id": cid,
#                     "document_count": 0,
#                     "total_chunks": 0
#                 }
#             collections[cid]["document_count"] += 1
#             collections[cid]["total_chunks"] += doc.chunk_count
        
#         return list(collections.values())

# document_service = DocumentService()