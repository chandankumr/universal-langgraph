# backend/app/services/feedback_service.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

class QueryFeedback(Base):
    __tablename__ = "query_feedback"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    message_id = Column(String, ForeignKey("messages.id"), nullable=False)
    
    # Feedback scores
    relevance_score = Column(Float)  # 1-5 stars
    helpfulness_score = Column(Float)  # 1-5 stars
    accuracy_score = Column(Float)  # 1-5 stars
    
    # Implicit signals
    was_copied = Column(Boolean, default=False)  # Did user copy the answer?
    was_regenerated = Column(Boolean, default=False)  # Did user regenerate?
    time_spent_seconds = Column(Integer)  # How long did they read?
    
    # Improvement data
    suggested_improvement = Column(Text)  # User's text feedback
    applied_to_model = Column(Boolean, default=False)  # Was this used for fine-tuning?
    
    created_at = Column(DateTime, default=datetime.utcnow)

class SearchAnalytics(Base):
    __tablename__ = "search_analytics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    query_text = Column(Text, nullable=False)
    retrieved_doc_ids = Column(String)  # JSON list
    final_answer_tokens = Column(Integer)
    retrieval_latency_ms = Column(Integer)
    llm_latency_ms = Column(Integer)
    total_latency_ms = Column(Integer)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)