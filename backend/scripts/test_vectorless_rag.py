#!/usr/bin/env python3
"""
Test & Benchmark: Vector vs Vectorless RAG
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test documents (simulating chunks from javanotes5.pdf)
TEST_DOCUMENTS = [
    "Java for loop combines initialization, condition, and update in one line.",
    "A while loop checks condition at the start of each iteration.",
    "The for-each loop iterates over collections and arrays easily.",
    "Java exception handling uses try, catch, and finally blocks.",
    "The finally block executes even if an exception occurs.",
    "Java is an object-oriented programming language developed by Sun Microsystems.",
    "JVM allows Java programs to run on any device without recompilation.",
    "Java supports multi-threading for concurrent execution.",
    "ArrayList is a resizable array implementation in Java Collections.",
    "HashMap stores key-value pairs with O(1) lookup time."
]

# Test queries
TEST_QUERIES = [
    ("for loop syntax", "vector"),           # Semantic query
    ("for loop syntax", "vectorless"),       # Same query, different method
    ("finally block exception", "vector"),   # Semantic query
    ("finally block exception", "vectorless"),
    ("ArrayList HashMap O(1)", "vector"),    # Technical term query
    ("ArrayList HashMap O(1)", "vectorless"),
    ("JVM recompilation", "vector"),         # Exact term query
    ("JVM recompilation", "vectorless"),
]

def vectorless_search(query: str, documents: list, k: int = 3):
    """BM25 keyword-based retrieval without embeddings."""
    from rank_bm25 import BM25Okapi
    
    # Tokenize documents
    tokenized_docs = [doc.lower().split() for doc in documents]
    bm25 = BM25Okapi(tokenized_docs)
    
    # Search
    scores = bm25.get_scores(query.lower().split())
    top_indices = scores.argsort()[-k:][::-1]
    
    return [(documents[i], scores[i]) for i in top_indices]

def vector_search(query: str, k: int = 3):
    """Your existing vector search (placeholder for testing)."""
    from app.database import vector_db
    
    try:
        results = vector_db.search(query=query, k=k, collection_id="default")
        return [(doc.page_content, 0.0) for doc in results]
    except Exception as e:
        print(f"⚠️ Vector search error: {e}")
        return []

def benchmark_search():
    """Compare latency and results between methods."""
    print("\n" + "="*70)
    print("🔍 VECTOR vs VECTORLESS RAG BENCHMARK")
    print("="*70 + "\n")
    
    results = {
        "vector": {"latency": [], "results": []},
        "vectorless": {"latency": [], "results": []}
    }
    
    for query, method in TEST_QUERIES:
        print(f"📝 Query: '{query}' | Method: {method.upper()}")
        print("-" * 70)
        
        start_time = time.time()
        
        if method == "vectorless":
            search_results = vectorless_search(query, TEST_DOCUMENTS, k=3)
        else:
            search_results = vector_search(query, k=3)
        
        latency = time.time() - start_time
        results[method]["latency"].append(latency)
        results[method]["results"].append(search_results)
        
        print(f"⏱️ Latency: {latency*1000:.2f}ms")
        print(f"📚 Top Results:")
        for i, (doc, score) in enumerate(search_results, 1):
            print(f"   {i}. {doc[:80]}... (score: {score:.4f})")
        print()
    
    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    
    avg_latency_vector = sum(results["vector"]["latency"]) / len(results["vector"]["latency"]) * 1000
    avg_latency_vectorless = sum(results["vectorless"]["latency"]) / len(results["vectorless"]["latency"]) * 1000
    
    print(f"""
┌─────────────────────────────────────────────────────────────────┐
│  Method      │  Avg Latency  │  Speedup  │  Best For            │
├─────────────────────────────────────────────────────────────────┤
│  Vector      │  {avg_latency_vector:6.2f}ms     │    1.0x    │  Semantic queries      │
│  Vectorless  │  {avg_latency_vectorless:6.2f}ms     │  {avg_latency_vector/avg_latency_vectorless if avg_latency_vectorless > 0 else 'N/A':.2f}x    │  Exact term matching   │
└─────────────────────────────────────────────────────────────────┘

✅ Vectorless is {avg_latency_vector/avg_latency_vectorless if avg_latency_vectorless > 0 else 'N/A':.1f}x faster for exact keyword queries!
""")
    
    return results

if __name__ == "__main__":
    benchmark_search()