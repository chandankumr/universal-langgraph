import os
import sys
import json
from dotenv import load_dotenv
from datasets import Dataset

# ✅ 1. Load .env file explicitly
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

if not os.getenv("GROQ_API_KEY"):
    print("❌ ERROR: GROQ_API_KEY not found in .env file!")
    sys.exit(1)

print("✅ GROQ_API_KEY loaded successfully.")

# ✅ 2. Imports
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

# ✅ 3. Load Evaluation Dataset
dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests', 'evaluation_dataset.json')

if not os.path.exists(dataset_path):
    print(f"❌ ERROR: Dataset not found at {dataset_path}")
    sys.exit(1)

with open(dataset_path, 'r') as f:
    eval_data = json.load(f)

# ✅ 4. Convert to HuggingFace Dataset format
dataset_dict = {
    "question": [item["question"] for item in eval_data],
    "answer": [item["answer"] for item in eval_data],
    "contexts": [item["contexts"] for item in eval_data],
    "reference": [item["reference"] for item in eval_data]
}
dataset = Dataset.from_dict(dataset_dict)

# ✅ 5. Initialize LLM (Groq) and Embeddings (Local HuggingFace)
eval_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY")
)

# Use the SAME embedding model you use for ChromaDB
# This avoids needing an OpenAI API key
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

print("✅ Local Embeddings loaded (BAAI/bge-small-en-v1.5)")

# ✅ 6. Run Evaluation
print("\n🔍 Starting RAGAS Evaluation...")
print(f"📊 Evaluating {len(eval_data)} test questions...\n")

try:
    results = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ],
        llm=eval_llm,
        embeddings=embeddings  # <-- CRITICAL: Pass local embeddings here
    )

    # ✅ 7. Print Results (Fixed to handle lists)
    print("\n" + "="*50)
    print("📈 RAGAS EVALUATION RESULTS")
    print("="*50)
    
    # Helper function to extract score from list or float
    def get_score(val):
        if isinstance(val, list):
            return val[0] if len(val) > 0 else 0.0
        return float(val)

    faithfulness_score = get_score(results['faithfulness'])
    relevancy_score = get_score(results['answer_relevancy'])
    precision_score = get_score(results['context_precision'])
    recall_score = get_score(results['context_recall'])

    print(f"Faithfulness:        {faithfulness_score:.3f}")
    print(f"Answer Relevancy:    {relevancy_score:.3f}")
    print(f"Context Precision:   {precision_score:.3f}")
    print(f"Context Recall:      {recall_score:.3f}")
    print("="*50)

    # ✅ 8. Save results
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests', 'evaluation_results.json')
    with open(output_path, 'w') as f:
        json.dump({
            "faithfulness": faithfulness_score,
            "answer_relevancy": relevancy_score,
            "context_precision": precision_score,
            "context_recall": recall_score,
            "total_questions": len(eval_data),
            "note": "Scores extracted from RAGAS evaluation (handled list/float conversion)"
        }, f, indent=2)

    print(f"\n✅ Results saved to {output_path}")
    
except Exception as e:
    print(f"\n❌ Evaluation failed: {e}")
    import traceback
    traceback.print_exc()





















# import json
# import os
# import sys
# from datasets import Dataset
# from ragas import evaluate
# from ragas.metrics import (
#     faithfulness,
#     answer_relevancy,
#     context_precision,
#     context_recall
# )
# from langchain_openai import ChatOpenAI
# from langchain_core.prompts import ChatPromptTemplate
# # from ..app.config import settings

# # Add backend to path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# # Load evaluation dataset
# with open('tests/eval_dataset.json', 'r') as f:
#     eval_data = json.load(f)

# # Convert to HuggingFace Dataset format
# dataset_dict = {
#     "question": [item["question"] for item in eval_data],
#     "answer": [item["answer"] for item in eval_data],
#     "contexts": [item["contexts"] for item in eval_data]
# }
# dataset = Dataset.from_dict(dataset_dict)

# # Initialize LLM for evaluation (uses your Groq key)
# from langchain_groq import ChatGroq
# import os

# eval_llm = ChatGroq(
#     model="llama-3.1-8b-instant",
#     api_key=os.getenv("GROQ_API_KEY")
#     # api_key = settings.GROQ_API_KEY
# )

# # Run Evaluation
# print("🔍 Starting RAGAS Evaluation...")
# print(f"📊 Evaluating {len(eval_data)} test questions...\n")

# results = evaluate(
#     dataset,
#     metrics=[
#         faithfulness,
#         answer_relevancy,
#         context_precision,
#         context_recall
#     ],
#     llm=eval_llm
# )

# # Print Results
# print("\n" + "="*50)
# print("📈 RAGAS EVALUATION RESULTS")
# print("="*50)
# print(f"Faithfulness:        {results['faithfulness']:.3f}")
# print(f"Answer Relevancy:    {results['answer_relevancy']:.3f}")
# print(f"Context Precision:   {results['context_precision']:.3f}")
# print(f"Context Recall:      {results['context_recall']:.3f}")
# print("="*50)

# # Interpretation
# print("\n📋 INTERPRETATION:")
# print("- Faithfulness > 0.8: Low hallucination ✅")
# print("- Answer Relevancy > 0.8: Answers are on-topic ✅")
# print("- Context Precision > 0.8: Relevant chunks ranked high ✅")
# print("- Context Recall > 0.8: Most relevant info retrieved ✅")

# # Save results to JSON
# with open('tests/evaluation_results.json', 'w') as f:
#     json.dump({
#         "faithfulness": float(results['faithfulness']),
#         "answer_relevancy": float(results['answer_relevancy']),
#         "context_precision": float(results['context_precision']),
#         "context_recall": float(results['context_recall']),
#         "total_questions": len(eval_data)
#     }, f, indent=2)

# print("\n✅ Results saved to tests/evaluation_results.json")