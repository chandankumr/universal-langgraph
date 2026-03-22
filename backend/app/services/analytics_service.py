# backend/app/services/analytics_service.py
import tiktoken

class TokenAnalytics:
    """Track token usage at granular level (Karpathy-style transparency)."""
    
    def __init__(self):
        self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def analyze_query(self, query: str, retrieved_docs: list, answer: str) -> Dict[str, Any]:
        """Analyze token usage for a query."""
        query_tokens = self.encoder.encode(query)
        answer_tokens = self.encoder.encode(answer)
        
        doc_tokens = []
        for doc in retrieved_docs:
            doc_tokens.extend(self.encoder.encode(doc.page_content))
        
        return {
            "query_tokens": len(query_tokens),
            "answer_tokens": len(answer_tokens),
            "context_tokens": len(doc_tokens),
            "total_tokens": len(query_tokens) + len(doc_tokens) + len(answer_tokens),
            "estimated_cost_usd": self._calculate_cost(len(query_tokens), len(doc_tokens), len(answer_tokens)),
            "token_efficiency": len(answer_tokens) / max(len(doc_tokens), 1),  # Lower is better
            "query_tokens_preview": self.encoder.decode(query_tokens[:10]) + "...",
            "answer_tokens_preview": self.encoder.decode(answer_tokens[:10]) + "..."
        }
    
    def _calculate_cost(self, input_tokens: int, context_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost (OpenAI pricing)."""
        # GPT-4o pricing (example)
        input_cost = (input_tokens + context_tokens) * 0.000005  # $5 per 1M tokens
        output_cost = output_tokens * 0.000015  # $15 per 1M tokens
        return round(input_cost + output_cost, 6)

analytics_service = TokenAnalytics()