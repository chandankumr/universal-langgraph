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
    
    # def execute_query(
    #     self,
    #     db: Session,
    #     user_id: str,
    #     request_data  # Can be Pydantic OR dict
    # ) -> Dict[str, Any]:
    #     """
    #     Execute a query through LangGraph workflow.
        
    #     Args:
    #         db: Database session
    #         user_id: User ID
    #         request_data: Query request data
            
    #     Returns:
    #         Query result with answer and metadata
    #     """

    #     # Handle both Pydantic and dict
    #     if hasattr(request_data, 'dict'):
    #         # It's a Pydantic model
    #         data = request_data.dict() if hasattr(request_data, 'dict') else vars(request_data)
    #     else:
    #         # It's already a dict
    #         data = request_data

    #     thread_id = data.get("thread_id") or str(uuid.uuid4())
    #     question = data.get("question", "")
    #     # provider = data.get("provider", "openai")
    #     # collection_filter = data.get("collection_filter")
    #     conversation_history = data.get("conversation_history", [])

    #     # ✅ Get user's preferred model from database
    #     from app.models import UserPreference
    #     pref = db.query(UserPreference).filter(
    #         UserPreference.user_id == user_id
    #     ).first()
        
    #     provider = pref.preferred_llm_provider if pref else "ollama"
    #     model = pref.preferred_llm_model if pref else settings.OLLAMA_MODEL

    #     # ✅ Get API key if needed
    #     api_key = None
    #     if pref and pref.custom_api_keys and provider in pref.custom_api_keys:
    #         from app.encryption import encryption_service
    #         api_key = encryption_service.decrypt(pref.custom_api_keys[provider])

    #     config = {
    #         "configurable": {
    #             "thread_id": thread_id
    #         }
    #     }
        
    #     # Build initial state
    #     messages = conversation_history or []
    #     messages.append({"role": "user", "content": question})
        
    #     inputs = {
    #         "messages": messages,
    #         "question": question,
    #         # "generated_queries": [],
    #         "documents": [],
    #         "answer": "",
    #         # "relevance_grade": "",
    #         # "hallucination_grade": "",
    #         # "iteration_count": 0,
    #         "router_decision": "",
    #         # "collection_filter": collection_filter
    #     }
        
    #     try:
    #         if not rag_graph:
    #             return {
    #                 "thread_id": thread_id,
    #                 "question": question,
    #                 "answer": "LangGraph not initialized. Check configuration.",
    #                 "status": "error"
    #             }
    #         # # Stream execution
    #         # stream_output = {}
    #         # for event in rag_graph.stream(inputs, config):
    #         #     stream_output.update(event)
            
    #         # Get final state
    #         # final_state = rag_graph.get_state(config)
    #         # state_values = final_state.values if final_state else {}
    #         final_state = rag_graph.invoke(inputs, config)

    #         # result = {
    #         #     "thread_id": thread_id,
    #         #     "question": question,
    #         #     "answer": state_values.get("answer", ""),
    #         #     "router_decision": state_values.get("router_decision", "search"),
    #         #     "documents_retrieved": len(state_values.get("documents", [])),
    #         #     "iterations": state_values.get("iteration_count", 0),
    #         #     "collection_filter": collection_filter,
    #         #     "status": "success"
    #         # }

    #         result = {
    #             "thread_id": thread_id,
    #             "question": question,
    #             "answer": final_state.get("answer", ""),
    #             "router_decision": final_state.get("router_decision", "search"),
    #             "documents_retrieved": len(final_state.get("documents", [])),
    #             "iterations": 0,
    #             "model_used": f"{provider}/{model}",
    #             "status": "success"
    #         }
            
    #         # logger.info(f"Query completed: thread={thread_id}, iterations={result['iterations']}")
    #         logger.info(f"✅ Query completed: thread={thread_id}, model={provider}/{model}")
    #         return result
            
    #     except Exception as e:
    #         logger.error(f"Query execution error: {str(e)}")
    #         return {
    #             "thread_id": thread_id,
    #             "question": question,
    #             "answer": f"Error processing query: {str(e)}",
    #             "status": "error"
    #         }

    def execute_query(self, db: Session, user_id: str, request_data) -> Dict[str, Any]:
        # Convert Pydantic to dict
        if hasattr(request_data, 'model_dump'):
            data = request_data.model_dump()
        else:
            data = request_data.dict() if hasattr(request_data, 'dict') else request_data
        
        thread_id = data.get("thread_id") or str(uuid.uuid4())
        question = data.get("question", "")
        conversation_history = data.get("conversation_history", [])
        search_method = data.get("search_method", "vector")
        
        # ✅ 1. Get User Preferences
        from app.models import UserPreference
        pref = db.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).first()
        
        # provider = pref.preferred_llm_provider if pref else "ollama"
        # model = pref.preferred_llm_model if pref else None
        provider = pref.preferred_llm_provider if pref else "groq" 
        model = pref.preferred_llm_model if pref else "llama-3.1-8b-instant"

        # ✅ 2. Decrypt API Key if needed
        api_key = None
        if pref and pref.custom_api_keys and provider in pref.custom_api_keys:
            from app.encryption import encryption_service
            try:
                api_key = encryption_service.decrypt(pref.custom_api_keys[provider])
                logger.info(f"🔑 Decrypted API key for {provider}")
            except Exception as e:
                logger.error(f"Failed to decrypt key: {e}")
        
        # Fallback to env vars if no user key saved (for testing)
        if not api_key:
            if provider == "google" and settings.GOOGLE_API_KEY:
                api_key = settings.GOOGLE_API_KEY
            elif provider == "openai" and settings.OPENAI_API_KEY:
                api_key = settings.OPENAI_API_KEY
            elif provider == "groq" and settings.GROQ_API_KEY:
                api_key = settings.GROQ_API_KEY
                logger.info("🔑 Using Groq API Key from .env fallback")
            # Only try Ollama if explicitly requested (no key needed)
            elif provider == "ollama":
                logger.warning("⚠️ Using Ollama (ensure 'ollama serve' is running)")

            if not api_key and provider != "ollama":
                return {
                    "thread_id": thread_id,
                    "question": question,
                    "answer": f"Error: {provider} API Key missing. Please configure in settings.",
                    "status": "error"
                }
        
        config = {
            "configurable": {
                "thread_id": thread_id,
                # ✅ 3. Pass LLM config to graph nodes
                "llm_provider": provider,
                "llm_model": model,
                "llm_api_key": api_key,
                "search_method": search_method
            }
        }
        
        messages = conversation_history or []
        messages.append({"role": "user", "content": question})
        
        inputs = {
            "messages": messages,
            "question": question,
            "answer": "",
            "router_decision": "",
            "documents": [],
            "search_method": search_method
        }
        
        try:
            if not rag_graph:
                return {"answer": "LangGraph not initialized.", "status": "error"}
            
            # ✅ 4. Invoke with config
            final_state = rag_graph.invoke(inputs, config)
            
            result = {
                "thread_id": thread_id,
                "question": question,
                "answer": final_state.get("answer", ""),
                "router_decision": final_state.get("router_decision", "search"),
                "documents_retrieved": len(final_state.get("documents", [])),
                "model_used": f"{provider}/{model}",
                "search_method": search_method,
                "status": "success"
            }
            
            logger.info(f"✅ Query completed using {provider}/{model} | Method: {search_method}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Query execution error: {str(e)}")
            # Specific check for Ollama connection error
            if "Connection refused" in str(e) and provider == "ollama":
                return {
                    "thread_id": thread_id,
                    "question": question,
                    "answer": "Error: Could not connect to Ollama. Please run 'ollama serve' or switch to Groq in settings.",
                    "status": "error"
                }

            return {
                "thread_id": thread_id,
                "question": question,
                "answer": f"Error: {str(e)}",
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