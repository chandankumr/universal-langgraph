from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.graphs.rag_graph import rag_graph
from app.services.llm_service import llm_service
from app.services.vector_service import vector_service
from app.config import settings
import logging
import uuid

logger = logging.getLogger(__name__)

class GraphService:
    """LangGraph execution service."""
    
    def execute_query(
        self,
        db: Session,
        user_id: str,
        request_data  # Can be Pydantic OR dict
    ) -> Dict[str, Any]:
        """
        Execute a query through LangGraph workflow.
        
        Args:
            db: Database session
            user_id: User ID
            request_data: Query request data
            
        Returns:
            Query result with answer and metadata
        """

        # Handle both Pydantic and dict
        if hasattr(request_data, 'dict'):
            # It's a Pydantic model
            data = request_data.dict() if hasattr(request_data, 'dict') else vars(request_data)
        else:
            # It's already a dict
            data = request_data

        thread_id = data.get("thread_id") or str(uuid.uuid4())
        question = data.get("question", "")
        provider = data.get("provider", "openai")
        collection_filter = data.get("collection_filter")
        conversation_history = data.get("conversation_history", [])
        
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        # Build initial state
        messages = conversation_history or []
        messages.append({"role": "user", "content": question})
        
        inputs = {
            "messages": messages,
            "question": question,
            "generated_queries": [],
            "documents": [],
            "answer": "",
            "relevance_grade": "",
            "hallucination_grade": "",
            "iteration_count": 0,
            "router_decision": "",
            "collection_filter": collection_filter
        }
        
        try:
            # Stream execution
            stream_output = {}
            for event in rag_graph.stream(inputs, config):
                stream_output.update(event)
            
            # Get final state
            final_state = rag_graph.get_state(config)
            state_values = final_state.values if final_state else {}
            
            result = {
                "thread_id": thread_id,
                "question": question,
                "answer": state_values.get("answer", ""),
                "router_decision": state_values.get("router_decision", "search"),
                "documents_retrieved": len(state_values.get("documents", [])),
                "iterations": state_values.get("iteration_count", 0),
                "collection_filter": collection_filter,
                "status": "success"
            }
            
            logger.info(f"Query completed: thread={thread_id}, iterations={result['iterations']}")
            return result
            
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            return {
                "thread_id": thread_id,
                "question": question,
                "answer": f"Error processing query: {str(e)}",
                "status": "error"
            }
    
    def get_conversation_history(self, db: Session, thread_id: str) -> List[dict]:
        """Retrieve conversation history for a thread."""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = rag_graph.get_state(config)
            if state and state.values:
                return state.values.get("messages", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get conversation history: {str(e)}")
            return []
    
    def delete_thread(self, thread_id: str) -> bool:
        """Delete a conversation thread."""
        logger.info(f"Thread deletion requested: {thread_id}")
        return True

graph_service = GraphService()