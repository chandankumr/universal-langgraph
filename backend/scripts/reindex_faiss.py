import os
import sys
from dotenv import load_dotenv

# Load env
load_dotenv()

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

print("🚀 Starting FAISS Re-Indexing...")

# 1. Load PDF
pdf_path = "/Users/chandankumar/Documents/universal-langgraph/universal-langgraph/backend/data/javanotes5.pdf" # Update path if different
if not os.path.exists(pdf_path):
    print(f"❌ PDF not found at {pdf_path}")
    sys.exit(1)

loader = PyPDFLoader(pdf_path)
docs = loader.load()
print(f"📄 Loaded {len(docs)} pages")

# 2. Split
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)
print(f"✂️ Created {len(chunks)} chunks")

# 3. Embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# 4. Create FAISS Index
print("🔨 Building FAISS index...")
db = FAISS.from_documents(chunks, embeddings)

# 5. Save
faiss_path = "./data/faiss_index"
os.makedirs(faiss_path, exist_ok=True)
db.save_local(faiss_path)

print(f"✅ FAISS Index saved to {faiss_path}")
print("🎉 Ready for MCP Server!")