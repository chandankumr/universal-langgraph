from typing import List, TypedDict, Annotated, Literal, Optional
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import RunnableConfig
from app.database import vector_db
from app.config import settings
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ==============================================================================
# STATE DEFINITION
# ==============================================================================

class RAGState(TypedDict):
    messages: Annotated[List[dict], add_messages]
    question: str
    answer: str
    router_decision: Literal["search", "chat"]
    documents: List[Document]

# ==============================================================================
# LLM SETUP - LAZY INITIALIZATION
# ==============================================================================

def get_llm(provider: str = "ollama", model: str = None, api_key: str = None):
    """Get LLM instance based on provider (called at request time, not import time)."""
    try:
        if provider == "ollama":
            llm = ChatOllama(
                model=model or settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0,
            )
            logger.info(f"✅ Ollama LLM initialized: {model or settings.OLLAMA_MODEL}")
            return llm
        
        elif provider == "openai":
            llm = ChatOpenAI(
                model=model or settings.OPENAI_MODEL,
                api_key=api_key or settings.OPENAI_API_KEY,
                temperature=0,
            )
            logger.info("✅ OpenAI LLM initialized")
            return llm
        
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=model or "gemini-1.5-flash",
                api_key=api_key or settings.GOOGLE_API_KEY,
                temperature=0,
            )
            logger.info("✅ Google Gemini LLM initialized")
            return llm
        
        elif provider == "azure_openai":
            from langchain_openai import AzureChatOpenAI
            llm = AzureChatOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=api_key or settings.AZURE_OPENAI_API_KEY,
                api_version="2024-02-15-preview",
                azure_deployment=model or "gpt-4o",
                temperature=0,
            )
            logger.info("✅ Azure OpenAI LLM initialized")
            return llm
        
        else:
            # Default to Ollama
            llm = ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0,
            )
            logger.info("✅ Default Ollama LLM initialized")
            return llm
            
    except Exception as e:
        logger.error(f"❌ LLM initialization failed: {str(e)}")
        return None

# def get_llm(db: Session, user_id: str):
#     """Get LLM based on user's saved preferences."""
#     from app.models import UserPreference
#     from app.encryption import encryption_service
    
#     # Get user preferences
#     pref = db.query(UserPreference).filter(
#         UserPreference.user_id == user_id
#     ).first()
    
#     provider = pref.preferred_llm_provider if pref else "ollama"
#     model = pref.preferred_llm_model if pref else settings.OLLAMA_MODEL
    
#     try:
#         if provider == "ollama":
#             return ChatOllama(
#                 model=model,
#                 base_url=settings.OLLAMA_BASE_URL,
#                 temperature=0
#             )
        
#         elif provider == "azure_openai":
#             api_key = None
#             if pref and pref.custom_api_keys and "azure_openai" in pref.custom_api_keys:
#                 api_key = encryption_service.decrypt(pref.custom_api_keys["azure_openai"])
#             else:
#                 api_key = settings.AZURE_OPENAI_API_KEY
            
#             return AzureChatOpenAI(
#                 azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
#                 api_key=api_key,
#                 api_version="2024-02-15-preview",
#                 azure_deployment=model,
#                 temperature=0
#             )
        
#         elif provider == "openai":
#             api_key = None
#             if pref and pref.custom_api_keys and "openai" in pref.custom_api_keys:
#                 api_key = encryption_service.decrypt(pref.custom_api_keys["openai"])
#             else:
#                 api_key = settings.OPENAI_API_KEY
            
#             return ChatOpenAI(
#                 model=model,
#                 api_key=api_key,
#                 temperature=0
#             )
        
#         elif provider == "groq":
#             api_key = None
#             if pref and pref.custom_api_keys and "groq" in pref.custom_api_keys:
#                 api_key = encryption_service.decrypt(pref.custom_api_keys["groq"])
            
#             return ChatGroq(
#                 model=model,
#                 api_key=api_key,
#                 temperature=0
#             )
        
#         elif provider == "google":
#             api_key = None
#             if pref and pref.custom_api_keys and "google" in pref.custom_api_keys:
#                 api_key = encryption_service.decrypt(pref.custom_api_keys["google"])
            
#             return ChatGoogleGenerativeAI(
#                 model=model,
#                 api_key=api_key,
#                 temperature=0
#             )
        
#         else:
#             logger.warning(f"Unknown provider: {provider}, falling back to Ollama")
#             return ChatOllama(model="llama3.1:8b", base_url=settings.OLLAMA_BASE_URL)
            
#     except Exception as e:
#         logger.error(f"LLM initialization failed: {e}")
#         return None

def get_llm_dynamic(provider: str, model: str, api_key: str = None):
    """Initialize LLM based on dynamic parameters."""
    try:
        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            if not api_key:
                raise ValueError("Google API Key missing")
            llm = ChatGoogleGenerativeAI(
                model=model or "gemini-1.5-flash",
                google_api_key=api_key,
                temperature=0
            )
            logger.info(f"✅ Initialized Google Gemini: {model}")
            return llm
        
        elif provider == "openai":
            from langchain_openai import ChatOpenAI
            if not api_key:
                raise ValueError("OpenAI API Key missing")
            llm = ChatOpenAI(
                model=model or "gpt-4o-mini",
                api_key=api_key,
                temperature=0
            )
            logger.info(f"✅ Initialized OpenAI: {model}")
            return llm
            
        elif provider == "azure_openai":
            from langchain_openai import AzureChatOpenAI
            # You would need to pass endpoint/deployment too for full dynamic support
            # For now, fallback to settings if azure selected
            llm = AzureChatOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=api_key or settings.AZURE_OPENAI_API_KEY,
                api_version="2024-02-15-preview",
                azure_deployment=model or "gpt-4o",
                temperature=0
            )
            logger.info(f"✅ Initialized Azure OpenAI: {model}")
            return llm

        elif provider == "groq":
            from langchain_groq import ChatGroq
            if not api_key:
                raise ValueError("Groq API Key missing")
            llm = ChatGroq(
                model=model or "llama3-8b-8192",
                groq_api_key=api_key,
                temperature=0
            )
            logger.info(f"✅ Initialized Groq: {model}")
            return llm

        else:
            # Default to Ollama for local
            from langchain_ollama import ChatOllama
            llm = ChatOllama(
                model=model or settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0
            )
            logger.info(f"✅ Initialized Ollama: {model}")
            return llm
            
    except Exception as e:
        logger.error(f"❌ LLM Init Failed ({provider}): {str(e)}")
        raise e

llm = get_llm()

# ==============================================================================
# NODES
# ==============================================================================

def router_node(state: RAGState):
    """Simple router."""
    question = state["question"].lower()
    
    if any(word in question for word in ["hi", "hello", "hey", "thanks", "bye"]):
        return {"router_decision": "chat"}
    else:
        return {"router_decision": "search"}

# def chat_node(state: RAGState):
#     """Handle casual conversation."""
#     # Get LLM at runtime (not import time)
#     llm = get_llm()
    
#     if llm:
#         try:
#             response = llm.invoke(state["messages"])
#             return {"answer": response.content, "messages": [response]}
#         except Exception as e:
#             logger.error(f"Chat error: {str(e)}")
    
#     return {"answer": "Hello! How can I help you today?", "messages": [AIMessage(content="Hello! How can I help you today?")]}

# def search_node(state: RAGState):
#     """Handle search queries."""
#     # Get LLM at runtime (not import time)
#     llm = get_llm()
    
#     if llm:
#         try:
#             response = llm.invoke(state["messages"])
#             return {"answer": response.content, "messages": [response]}
#         except Exception as e:
#             logger.error(f"Search error: {str(e)}")
    
#     return {"answer": "I don't have access to documents yet. Please upload some first.", "messages": [AIMessage(content="I don't have access to documents yet.")]}

# def search_node(state: RAGState):
#     """
#     CRITICAL: Search vector DB and generate answer from retrieved documents.
#     """
#     question = state["question"]
    
#     # Step 1: Search Vector DB (Chroma)
#     try:
#         retrieved_docs = vector_db.search(query=question, k=5, collection_id="default")
#         logger.info(f"🔍 Search returned {len(retrieved_docs)} documents")
#     except Exception as e:
#         logger.error(f"❌ Search error: {str(e)}")
#         retrieved_docs = []
    
#     # Step 2: Check if we found relevant documents
#     if not retrieved_docs:
#         return {
#             "answer": "I don't have access to documents yet. Please upload some first.",
#             "documents": [],
#             "messages": [AIMessage(content="I don't have access to documents yet. Please upload some first.")]
#         }
    
#     # Step 3: Get LLM (lazy initialization)
#     llm = get_llm(provider="ollama")  # Or get from user preferences
    
#     if not llm:
#         return {
#             "answer": "LLM not configured. Please check settings.",
#             "documents": retrieved_docs,
#             "messages": [AIMessage(content="LLM not configured.")]
#         }
    
#     # Step 4: Build context from retrieved documents
#     context = "\n\n".join([doc.page_content for doc in retrieved_docs[:3]])
    
#     # Step 5: Generate answer from context
#     prompt = f"""Answer the question based ONLY on the following context. If the answer is not in the context, say "I cannot find this information in the uploaded documents."

# Context:
# {context}

# Question: {question}

# Answer:"""
    
#     try:
#         response = llm.invoke(prompt)
#         logger.info(f"✅ Generated answer from {len(retrieved_docs)} documents")
        
#         return {
#             "answer": response.content,
#             "documents": retrieved_docs,
#             "messages": [response]
#         }
#     except Exception as e:
#         logger.error(f"❌ Generation error: {str(e)}")
#         return {
#             "answer": f"Error generating response: {str(e)}",
#             "documents": retrieved_docs,
#             "messages": [AIMessage(content=f"Error: {str(e)}")]
#         }

def search_node(state: RAGState, config: RunnableConfig):
    """
    Search vector DB and generate answer.
    Reads provider/model from config (passed by graph_service).
    """
    question = state["question"]
    
    # 1. Retrieve Documents
    try:
        # retrieved_docs = vector_db.search(query=question, k=15, collection_id="default")
        if len(question.split()) > 10: # Only rerank for long/complex questions
            retrieved_docs = vector_db.search_with_rerank(query=question, k=5, collection_id="default")
        else:
            retrieved_docs = vector_db.search(query=question, k=15, collection_id="default") # Fast vector search only
        
        logger.info(f"🔍 Search returned {len(retrieved_docs)} documents (after re-rank)")
    except Exception as e:
        logger.error(f"❌ Search error: {str(e)}")
        retrieved_docs = []
    
    if not retrieved_docs:
        return {
            "answer": "I don't have access to documents yet. Please upload some first.",
            "documents": [],
            "messages": [AIMessage(content="I don't have access to documents yet.")]
        }
    
    # 2. Get Dynamic LLM Config from RunnableConfig
    configurable = config.get("configurable", {})
    provider = configurable.get("llm_provider", "ollama")
    model = configurable.get("llm_model", None)
    api_key = configurable.get("llm_api_key", None)
    
    logger.info(f"🤖 Using LLM: {provider} / {model}")
    
    try:
        llm = get_llm_dynamic(provider, model, api_key)
        
        # 3. Build Context
        # context = "\n\n".join([doc.page_content for doc in retrieved_docs[:3]])
        # Build context from retrieved documents
        # Add separators so the AI knows where one chunk ends and another begins
        context_parts = []
        for i, doc in enumerate(retrieved_docs[:15]): # Ensure we use the new limit
            context_parts.append(f"[Source {i+1}]: {doc.page_content}")
        
        context = "\n\n".join(context_parts)

#         prompt = f"""Answer the question based ONLY on the following context. If the answer is not in the context, say "I cannot find this information in the uploaded documents."

# Context:
# {context}

# Question: {question}

# Answer:"""

        prompt = f"""You are an expert assistant. Answer the question based ONLY on the following context sources. 
        The context may be split across multiple sources. You MUST synthesize information from ALL relevant sources to provide a complete answer.
        If the answer requires combining facts from Source 1 and Source 5, do so.
        If the answer is not in ANY of the sources, say "I cannot find this information in the uploaded documents."

        Context Sources:
        {context}

        Question: {question}

        Comprehensive Answer:"""
        
        response = llm.invoke(prompt)
        logger.info(f"✅ Generated answer using {provider}")
        
        return {
            "answer": response.content,
            "documents": retrieved_docs,
            "messages": [response]
        }
        
    except Exception as e:
        logger.error(f"❌ Generation error: {str(e)}")
        return {
            "answer": f"Error generating response: {str(e)}",
            "documents": retrieved_docs,
            "messages": [AIMessage(content=f"Error: {str(e)}")]
        }

def chat_node(state: RAGState, config: RunnableConfig):
    """Handle casual conversation with dynamic LLM."""
    configurable = config.get("configurable", {})
    provider = configurable.get("llm_provider", "ollama")
    model = configurable.get("llm_model", None)
    api_key = configurable.get("llm_api_key", None)
    
    try:
        llm = get_llm_dynamic(provider, model, api_key)
        response = llm.invoke(state["messages"])
        return {"answer": response.content, "messages": [response], "documents": []}
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return {"answer": f"Error: {str(e)}", "messages": [AIMessage(content=f"Error: {str(e)}")], "documents": []}


# ==============================================================================
# GRAPH BUILDING
# ==============================================================================

def build_rag_graph():
    """Build and compile the LangGraph workflow."""
    
    workflow = StateGraph(RAGState)
    
    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("chat", chat_node)
    workflow.add_node("search", search_node)
    
    # Edges
    workflow.add_edge(START, "router")
    
    # Router conditional edges
    workflow.add_conditional_edges(
        "router",
        lambda x: x["router_decision"],
        {
            "chat": "chat",
            "search": "search"
        }
    )
    
    workflow.add_edge("chat", END)
    workflow.add_edge("search", END)
    
    # Compile with memory
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    logger.info("✅ LangGraph workflow compiled successfully")
    return app

# Singleton graph instance
try:
    rag_graph = build_rag_graph()
except Exception as e:
    logger.error(f"❌ Failed to build graph: {str(e)}")
    rag_graph = None


















# from typing import List, TypedDict, Annotated, Literal, Optional
# from langchain_openai import ChatOpenAI
# from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# from langchain_core.documents import Document
# from langgraph.graph import StateGraph, END, START
# from langgraph.graph.message import add_messages
# from app.database import vector_db
# from app.config import settings
# import logging

# logger = logging.getLogger(__name__)

# # ==============================================================================
# # STATE DEFINITION
# # ==============================================================================

# class RAGState(TypedDict):
#     messages: Annotated[List[dict], add_messages]
#     question: str
#     generated_queries: List[str]
#     documents: List[Document]
#     answer: str
#     relevance_grade: Literal["yes", "no"]
#     hallucination_grade: Literal["yes", "no"]
#     iteration_count: int
#     router_decision: Literal["search", "calculator", "chat"]
#     collection_filter: Optional[str]

# # ==============================================================================
# # LLM SETUP
# # ==============================================================================

# def get_llm():
#     """Get LLM based on settings."""
#     try:
#         llm = ChatOpenAI(
#             model=settings.OPENAI_MODEL,
#             temperature=0,
#             api_key=settings.OPENAI_API_KEY,
#             streaming=True
#         )
#         return llm
#     except Exception as e:
#         logger.error(f"Failed to initialize LLM: {str(e)}")
#         # Fallback to mock for testing
#         return None

# llm = get_llm()

# # ==============================================================================
# # NODES
# # ==============================================================================

# def router_node(state: RAGState):
#     """Route query to appropriate handler."""
#     question = state["question"]
    
#     # Simple routing logic
#     if any(word in question.lower() for word in ["calculate", "math", "sum", "multiply"]):
#         return {"router_decision": "calculator"}
#     elif any(word in question.lower() for word in ["hi", "hello", "hey", "thanks"]):
#         return {"router_decision": "chat"}
#     else:
#         return {"router_decision": "search"}

# def retrieve_node(state: RAGState):
#     """Retrieve documents from vector store."""
#     question = state["question"]
    
#     try:
#         # Use Chroma DB for retrieval
#         docs = vector_db.search(query=question, k=settings.MAX_RETRIEVAL_K)
#         logger.info(f"Retrieved {len(docs)} documents")
#         return {"documents": docs}
#     except Exception as e:
#         logger.error(f"Retrieval error: {str(e)}")
#         return {"documents": []}

# def generate_answer_node(state: RAGState):
#     """Generate answer from retrieved context."""
#     question = state["question"]
#     docs = state["documents"]
    
#     if docs and llm:
#         context = "\n\n".join([d.page_content for d in docs])
#         prompt = f"""
#         Answer the question based ONLY on the following context.
#         If the answer is not in the context, say "I cannot find this information."
        
#         Context:
#         {context}
        
#         Question: {question}
        
#         Answer:
#         """
#         try:
#             response = llm.invoke(prompt)
#             return {"answer": response.content, "messages": [AIMessage(content=response.content)]}
#         except Exception as e:
#             logger.error(f"Generation error: {str(e)}")
    
#     # Fallback response
#     fallback = "I don't have enough information to answer this question. Please upload relevant documents first."
#     return {"answer": fallback, "messages": [AIMessage(content=fallback)]}

# def chat_node(state: RAGState):
#     """Handle casual conversation."""
#     question = state["question"]
    
#     if llm:
#         try:
#             response = llm.invoke(state["messages"])
#             return {"answer": response.content, "messages": [response]}
#         except:
#             pass
    
#     return {"answer": "Hello! How can I help you today?", "messages": [AIMessage(content="Hello! How can I help you today?")]}

# def calculator_node(state: RAGState):
#     """Handle calculator queries."""
#     return {"answer": "For calculations, please use a calculator tool.", "messages": [AIMessage(content="For calculations, please use a calculator tool.")]}

# # ==============================================================================
# # GRAPH BUILDING
# # ==============================================================================

# def build_rag_graph():
#     """Build and compile the LangGraph workflow."""
    
#     workflow = StateGraph(RAGState)
    
#     # Add nodes
#     workflow.add_node("router", router_node)
#     workflow.add_node("retrieve", retrieve_node)
#     workflow.add_node("generate", generate_answer_node)
#     workflow.add_node("calculator", calculator_node)
#     workflow.add_node("chat", chat_node)
    
#     # Edges
#     workflow.add_edge(START, "router")
    
#     # Router conditional edges
#     workflow.add_conditional_edges(
#         "router",
#         lambda x: x["router_decision"],
#         {
#             "search": "retrieve",
#             "calculator": "calculator",
#             "chat": "chat"
#         }
#     )
    
#     workflow.add_edge("retrieve", "generate")
#     workflow.add_edge("calculator", END)
#     workflow.add_edge("chat", END)
#     workflow.add_edge("generate", END)
    
#     # Compile
#     from langgraph.checkpoint.memory import MemorySaver
#     memory = MemorySaver()
#     app = workflow.compile(checkpointer=memory)
    
#     logger.info("LangGraph workflow compiled successfully")
#     return app

# # Singleton graph instance
# rag_graph = build_rag_graph()


# def get_llm():
#     """Get LLM based on settings."""
#     try:
#         if settings.OLLAMA_BASE_URL:
#             llm = ChatOllama(
#                 model=settings.OLLAMA_MODEL,
#                 base_url=settings.OLLAMA_BASE_URL,
#                 temperature=0,
#             )
#             logger.info(f"✅ Ollama LLM initialized: {settings.OLLAMA_MODEL}")
#             return llm
#         elif settings.GROQ_API_KEY:
#             llm = ChatGroq(
#                 model=settings.GROQ_MODEL,
#                 api_key=settings.GROQ_API_KEY,
#                 temperature=0,
#             )
#             logger.info("✅ Groq LLM initialized")
#             return llm
#         elif settings.OPENAI_API_KEY:
#             llm = ChatOpenAI(
#                 model=settings.OPENAI_MODEL,
#                 temperature=0,
#                 api_key=settings.OPENAI_API_KEY,
#             )
#             logger.info("✅ OpenAI LLM initialized")
#             return llm
#         elif settings.GOOGLE_API_KEY:
#             llm = ChatGoogleGenerativeAI(
#                 model=settings.GOOGLE_MODEL,  # e.g. "gemini-pro"
#                 google_api_key=settings.GOOGLE_API_KEY,
#                 temperature=0,
#             )
#             logger.info(f"✅ Google Gemini LLM initialized: {settings.GOOGLE_MODEL}")
#             return llm
#         else:
#             logger.warning("⚠️ No OpenAI API key found")
#             return None
#     except Exception as e:
#         logger.error(f"❌ LLM initialization failed: {str(e)}")
#         return None