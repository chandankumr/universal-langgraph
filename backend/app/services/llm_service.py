from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from app.models import APIKey
from app.encryption import encryption_service
from sqlalchemy.orm import Session
from langchain_openai import AzureChatOpenAI
import logging

logger = logging.getLogger(__name__)

class LLMService:
    """Dynamic LLM provider based on user's API keys."""
    
    PROVIDER_CONFIG = {
        "openai": {
            "class": ChatOpenAI,
            "default_model": "gpt-4o",
            "key_name": "OPENAI_API_KEY"
        },
        "anthropic": {
            "class": ChatAnthropic,
            "default_model": "claude-3-5-sonnet-20240620",
            "key_name": "ANTHROPIC_API_KEY"
        },
        "google": {
            "class": ChatGoogleGenerativeAI,
            "default_model": "gemini-1.5-pro",
            "key_name": "GOOGLE_API_KEY"
        },
        "ollama": {
            "class": ChatOllama,
            "default_model": "llama3.1:8b",
            "key_name": None,  # No API key needed
            "base_url": "http://localhost:11434"
        },
        "groq": {
            "class": ChatGroq,
            "default_model": "llama-3.1-70b-versatile",
            "key_name": "GROQ_API_KEY"
        },
        "mistral": {
            "class": ChatMistralAI,
            "default_model": "mistral-large-latest",
            "key_name": "MISTRAL_API_KEY"
        },
        "azure_openai": {
            "class": AzureChatOpenAI,
            "default_model": "gpt-4o",
            "key_name": "AZURE_OPENAI_API_KEY",
            "requires_endpoint": True
        }
    }
    
    def get_llm(
        self, 
        db: Session, 
        user_id: str, 
        provider: str,
        model: Optional[str] = None,
        temperature: float = 0
    ):
        """
        Get LLM instance based on user's configured provider.
        Supports both cloud APIs and local GPU (Ollama).
        """
        if provider not in self.PROVIDER_CONFIG:
            raise ValueError(f"Unsupported provider: {provider}")
        
        config = self.PROVIDER_CONFIG[provider]
        
        # Get API key from database (if required)
        api_key = None
        if config.get("key_name"):
            api_key_record = db.query(APIKey).filter(
                APIKey.user_id == user_id,
                APIKey.provider == provider,
                APIKey.is_active == True
            ).first()
            
            if not api_key_record:
                raise ValueError(f"No active {provider} API key found for user")
            
            api_key = encryption_service.decrypt(api_key_record.encrypted_key)
        
        # Initialize LLM
        llm_class = config["class"]
        llm_model = model or config["default_model"]
        
        try:
            if provider == "ollama":
                llm = llm_class(
                    model=llm_model,
                    base_url=config.get("base_url", "http://localhost:11434"),
                    temperature=temperature,
                    streaming=True
                )
            elif provider == "azure_openai":
                llm = AzureChatOpenAI(
                    azure_endpoint=config["endpoint"],
                    api_key=api_key,
                    api_version="2024-02-15-preview",
                    azure_deployment="gpt-4o"
                )
            else:
                llm = llm_class(
                    model=llm_model,
                    api_key=api_key,
                    temperature=temperature,
                    streaming=True
                )
            
            logger.info(f"Initialized {provider} LLM: {llm_model}")
            return llm
            
        except Exception as e:
            logger.error(f"Failed to initialize {provider} LLM: {str(e)}")
            raise ValueError(f"LLM initialization failed: {str(e)}")
    
    def test_connection(self, db: Session, user_id: str, provider: str) -> Dict[str, Any]:
        """Test if the API key/connection works."""
        try:
            llm = self.get_llm(db, user_id, provider)
            # Simple test query
            response = llm.invoke("Say 'connection test successful' in exactly 3 words")
            return {
                "success": True,
                "provider": provider,
                "message": "Connection successful"
            }
        except Exception as e:
            return {
                "success": False,
                "provider": provider,
                "error": str(e)
            }
    
    def list_available_models(self, provider: str) -> list:
        """List available models for a provider."""
        # In production, fetch from provider API
        model_lists = {
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
            "google": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"],
            "ollama": ["llama3.1:8b", "llama3.1:70b", "mistral:7b", "phi3:mini", "gemma2:9b"],
            "groq": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
            "mistral": ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"]
        }
        return model_lists.get(provider, [])

llm_service = LLMService()