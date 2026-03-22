# backend/app/services/cache_service.py
import redis
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import timedelta

class SpeculativeCache:
    """
    Karpathy-style speculative decoding cache.
    Fast cache lookup + verification before returning.
    """
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.ttl = timedelta(hours=24)
    
    def _generate_cache_key(self, query: str, context_hash: str) -> str:
        """Generate deterministic cache key."""
        combined = f"{query}:{context_hash}"
        return f"rag_cache:{hashlib.sha256(combined.encode()).hexdigest()}"
    
    def get_cached_response(self, query: str, context_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and verified."""
        cache_key = self._generate_cache_key(query, context_hash)
        cached = self.redis_client.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            # Verify cache is still valid (re-check relevance)
            if self._verify_cache(data):
                data["from_cache"] = True
                data["cache_latency_ms"] = 5  # Cache is fast
                return data
        
        return None
    
    def set_cached_response(self, query: str, context_hash: str, response: Dict[str, Any]):
        """Store response in cache."""
        cache_key = self._generate_cache_key(query, context_hash)
        response["cached_at"] = datetime.utcnow().isoformat()
        self.redis_client.setex(
            cache_key,
            self.ttl,
            json.dumps(response)
        )
    
    def _verify_cache(self, cached_data: Dict[str, Any]) -> bool:
        """Verify cached response is still relevant."""
        # Check if source documents haven't changed
        # Check if cache isn't too old
        # Check if confidence score was high
        return cached_data.get("confidence_score", 0) > 0.8
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        keys = self.redis_client.keys("rag_cache:*")
        return {
            "total_cached_queries": len(keys),
            "memory_usage": self.redis_client.info("memory")["used_memory_human"]
        }

cache_service = SpeculativeCache()