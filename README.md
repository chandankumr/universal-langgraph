# 🌐 Universal LangGraph AI Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/FastAPI-Production-green?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-Agentic_AI-blue?style=for-the-badge" alt="LangGraph" />
  <img src="https://img.shields.io/badge/Azure_OpenAI-Supported-0078D4?style=for-the-badge&logo=microsoft-azure" alt="Azure OpenAI" />
  <img src="https://img.shields.io/badge/RAG-Pipeline-orange?style=for-the-badge" alt="RAG Pipeline" />
  <img src="https://img.shields.io/badge/Docker-Kubernetes-red?style=for-the-badge&logo=docker" alt="Docker" />
  <img src="https://img.shields.io/badge/License-MIT-purple?style=for-the-badge" alt="License MIT" />
</p>

<p align="center">
  <strong>Enterprise-Ready Agentic AI Platform with Multi-Agent Workflows, Hybrid Search & Re-Ranking</strong>
</p>

<p align="center">
  <a href="#-live-demo--screenshots">View Demo</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-contact">Contact</a>
</p>

---

## 🎥 Live Demo & Screenshots

### 🔍 Querying a 699-Page Technical Manual

*Successfully retrieved and synthesized information from a 5MB PDF (`javanotes5.pdf`) using Hybrid Search + Re-Ranking.*

- **Challenge:** Accurately finding specific programming concepts scattered across 699 pages
- **Solution:** Retrieved 45 candidates, re-ranked to top 5 using `ms-marco-MiniLM` for maximum precision
- **Performance:** Warm cache response time < **3 seconds**

<p align="center">
  <img src="docs/java_query.png" width="85%" alt="Java Query Demo" />
</p>

---

### 🤖 MCP Server + Claude Desktop Integration

**✅ Production Ready** — Exposes RAG system as a universal AI tool via Model Context Protocol.

| Metric | Value |
| :--- | :--- |
| **Document Size** | 699 pages (5.2 MB) |
| **Chunks Indexed** | 2,632 |
| **Search Latency** | < 2 seconds |
| **Vector Store** | FAISS + ChromaDB fallback |

<p align="center">
  <img src="docs/mcp-claude-demo.png" width="85%" alt="MCP Claude Demo" />
</p>

---

### 📄 Multi-Document Context Handling

*System distinguishes between general programming concepts and specific implementation details within large textbooks.*

<p align="center">
  <img src="docs/query2.png" width="85%" alt="Multi-Document Query" />
</p>

> **Query:** "Explain how Java handles exception handling using try, catch, and finally. When is the finally block executed?"
>
> **Result:** Synthesized accurate definitions from multiple chapters.

---

### 🎬 Full Walkthrough Video

[![Watch the Demo](https://img.shields.io/badge/Watch-Demo_Video-red?style=for-the-badge&logo=google-drive)](https://drive.google.com/file/d/1S9HhA4N-qPvxwX_JpdEBABeQqdyk72BE/view?usp=sharing)

*See the system ingest a 700-page PDF, switch models to Groq, and answer complex technical queries.*

---

## 🚀 Overview

A **production-grade agentic AI orchestration platform** built for enterprise deployment. Designed to execute **autonomous multi-agent workflows** with Retrieval-Augmented Generation (RAG).

### Key Capabilities

- **Hybrid Search + Re-Ranking:** Combines vector similarity with Cross-Encoder re-ranking (`ms-marco-MiniLM`) to ensure the most relevant chunks are selected, even from 600+ page documents
- **MCP Integration:** Exposes RAG system as universal tool for AI assistants (Claude Desktop, etc.)
- **Dual Vector Store:** FAISS (primary, file-based) + ChromaDB (fallback, database) for maximum flexibility
- **Smart Fallbacks:** Gracefully degrades to standard vector search if advanced libraries encounter version conflicts, ensuring 100% uptime
- **Context Optimization:** Dynamically adjusts retrieval count (`k=15`) and uses synthesis prompts to combine scattered facts across multiple document chunks
- **Multi-Provider Support:** Switch seamlessly between Groq (Cloud), Ollama (Local), and Azure OpenAI without restarting services

---

## 🏆 Key Highlights

| Feature | Implementation | Enterprise Value |
| :--- | :--- | :--- |
| **Hybrid Search** | Vector DB + Cross-Encoder Re-Ranker | High precision on large docs |
| **MCP Server** | Model Context Protocol | Universal AI tool interoperability |
| **Multi-Agent Workflows** | LangGraph with routing, retrieval, generation, self-correction | Automates complex workflows |
| **LLM Flexibility** | Azure, OpenAI, Google, Groq, Ollama | Cost optimization & data privacy |
| **Security** | JWT auth, encrypted API keys, multi-tenant isolation | Production-ready security |
| **Deployment** | Docker, GPU support (NVIDIA/AMD ROCm) | Scalable infrastructure |
| **Monitoring** | Token analytics, structured logging, latency tracking | Full observability |
| **Quality Metrics** | RAGAS evaluation (Faithfulness, Relevancy, Precision, Recall) | Measurable production quality |

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph ClientLayer ["🖥️ Client Layer"]
        direction TB
        WebUI["Web Interface (React)"]
        Claude["Claude Desktop (MCP Client)"]
    end

    subgraph Backend ["⚙️ Core Backend (FastAPI)"]
        direction TB
        API["REST API Gateway"]
        Auth["Auth & Security (JWT)"]
        Graph["LangGraph Orchestrator"]
        Router["Intelligent Router"]
        Retriever["Hybrid Retriever + Re-Ranker"]
        Generator["LLM Generator"]
    end

    subgraph DataLayer ["💾 Data & Models Layer"]
        direction TB
        Chroma[("ChromaDB (Fallback)")]
        Postgres[("PostgreSQL (Docs & Users)")]
        Groq["Groq Cloud (Llama 3)"]
        Ollama["Ollama (Local)"]
        Azure["Azure OpenAI"]
    end

    subgraph MCPLayer ["🤖 MCP Integration Layer"]
        direction TB
        MCPServer["MCP Server (Python)"]
        FAISS["FAISS Vector Store (Primary)"]
    end

    WebUI -->|HTTP/JSON| API
    Claude -->|MCP Protocol| MCPServer
    
    API --> Auth
    Auth --> Graph
    Graph --> Router
    
    Router -->|Query| Retriever
    Retriever -->|Primary| FAISS
    Retriever -->|Fallback| Chroma
    Retriever -.->|Metadata| Postgres
    
    Router -->|Context + Prompt| Generator
    Generator --> Groq
    Generator --> Ollama
    Generator --> Azure
    
    Generator -->|Stream Response| API
    API -->|SSE Stream| WebUI
    
    MCPServer -->|Direct Search| FAISS
    MCPServer -.->|Fallback| API
    Generator -->|JSON Response| MCPServer

    classDef darkBg fill:#1e1e2e,stroke:#f5c2e7,stroke-width:2px,color:#ffffff;
    classDef client fill:#89b4fa,stroke:#ffffff,stroke-width:2px,color:#000000,font-weight:bold;
    classDef mcp fill:#fab387,stroke:#ffffff,stroke-width:2px,color:#000000,font-weight:bold;
    classDef backend fill:#a6e3a1,stroke:#ffffff,stroke-width:2px,color:#000000,font-weight:bold;
    classDef data fill:#cba6f7,stroke:#ffffff,stroke-width:2px,color:#000000,font-weight:bold;

    class ClientLayer,Backend,DataLayer,MCPLayer darkBg;
    class WebUI,Claude client;
    class MCPServer,FAISS mcp;
    class API,Auth,Graph,Router,Retriever,Generator backend;
    class Chroma,Postgres,Groq,Ollama,Azure data;
    
    linkStyle default stroke:#ffffff,stroke-width:2px;
```

<!-- ```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ️ CLIENT LAYER                                     │
│  [ Web UI (React) ]           [ Claude Desktop (MCP Client) ]               │
└────────────┬──────────────────────────────┬────────────────────────────────┘
             │ HTTP/JSON                    │ MCP Protocol
             ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      🤖 INTEGRATION LAYER                                   │
│  [ FastAPI Gateway ] <───────> [ MCP Server (Python) ]                      │
│  (Auth, Validation, SSE)           (Direct FAISS Access)                    │
└────────────┬──────────────────────────────┬────────────────────────────────┘
             │                              │
             ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ⚙️ LANGGRAPH ORCHESTRATOR                              │
│                                                                             │
│   [ Router ] ──► [ Hybrid Retriever ] ──► [ Re-Ranker (Cross-Encoder) ]    │
│       │                │                          │                         │
│       │                ▼                          ▼                         │
│       │      [ FAISS (Primary) ]        [ ChromaDB (Fallback) ]            │
│       │                │                          │                         │
│       └────────────────┴───────────────┬──────────┘                         │
│                                        ▼                                    │
│                               [ LLM Generator ]                             │
│                          (Groq • Ollama • Azure)                            │
└─────────────────────────────────────────────────────────────────────────────┘
             │                              │
             ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      💾 DATA & PERSISTENCE                                  │
│  [ PostgreSQL ] (Users, Docs, Metadata)                                     │
│  [ Local Files ] (FAISS Index, PDFs)                                        │
└─────────────────────────────────────────────────────────────────────────────┘
``` -->

---

## ⚙️ Features

### 🤖 Agentic AI Workflows
- Multi-agent orchestration using LangGraph for complex task decomposition
- Intelligent routing & query classification for optimal path selection
- Self-correction loops (critic nodes) for quality assurance
- Multi-step reasoning workflows for complex problem solving
- oMemory with conversation history for contextual interactions  

### 🔍 Advanced RAG Pipeline
- Hybrid Search: Combines dense vector retrieval with sparse keyword matching for comprehensive coverage
- Re-Ranking: Uses cross-encoder/ms-marco-MiniLM to re-score top candidates for higher accuracy
- Parent-Child Indexing: Retrieves small chunks for search but passes large parent contexts to the LLM
- Document Ingestion: Supports PDF, TXT, DOCX, MD with smart blank-page filtering
- FAISS Integration: File-based vector store for low-overhead MCP deployments
- Smart Chunking: Dynamic chunk sizes based on content semantics

### 🔌 Model-Agnostic Inference
- Cloud Providers: Azure OpenAI, OpenAI GPT-4o, Google Gemini, Groq (Llama 3)
- Local Deployment: Ollama (Llama 3, Mistral, Phi3) running on CPU/GPU
- Automatic Fallback: Switches providers on rate limits or failures
- Cost Optimization: Route simple queries to local models, complex to cloud 

### 🔐 Security
- JWT authentication with role-based access control
- AES-256 encryption for stored API keys
- Multi-tenant data isolation for enterprise deployments
- Comprehensive audit logging for compliance
- Rate limiting & request throttling

### 🚀 Deployment
- Docker & Docker Compose setup for consistent environments
- GPU Support: NVIDIA CUDA and AMD ROCm for accelerated inference
- Kubernetes-ready architecture for horizontal scaling
- Health checks & readiness probes for production monitoring

---

## ⚙️ Quick Start

### 📦 Prerequisites
- Docker & Docker Compose  
- Python 3.11+  
- Git  

---

### 1️⃣ Clone Repository
```bash
git clone https://github.com/chandankumr/universal-langgraph.git
cd universal-langgraph
```

### 2️⃣ Configure Environment
```bash
cd backend
cp .env.example .env
```
#### Edit .env:

```env
# For Groq (Recommended for Demo)
GROQ_API_KEY=gsk_your_key_here

# OR For Local Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/langgraph_platform

# Vector Store
CHROMA_PERSIST_DIR=./data/chroma_db
```

### 3️⃣ Deploy
```bash
chmod +x deploy.sh
./deploy.sh
```

#### GPU Deployment
```bash
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

#### AMD ROCm
```bash
docker-compose -f docker-compose.yml -f docker-compose.rocm.yml up -d
```

### 4️⃣ Access

| Service | URL |
|--------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| Docs | http://localhost:8000/docs |

---

### 5️⃣ MCP Server Setup (Optional)

##### Configure Claude Desktop by adding to ~/Library/Application Support/Claude/claude_desktop_config.json:

```json
{
  "mcpServers": {
    "langgraph-rag": {
      "command": "python",
      "args": ["backend/mcp_server.py"]
    }
  }
}
```

---

## 📁 Project Structure

```text
universal-langgraph/
├── backend/
│   ├── app/
│   │   ├── graphs/
│   │   │   ├── rag_graph.py
│   │   │   └── auto_research_graph.py
│   │   ├── services/
│   │   │   ├── llm_service.py
│   │   │   ├── vector_service.py
│   │   │   └── document_service.py
│   │   ├── main.py
│   │   ├── auth.py
│   │   └── models.py
│   ├── data/
│   │   ├── chroma_db/
│   │   └── faiss_index/
│   ├── scripts/
│   │   ├── evaluate_rag.py
│   │   └── reindex_faiss.py
│   ├── tests/
│   ├── mcp_server.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── App.jsx
│   └── package.json
├── docs/
│   ├── java_query.png
│   ├── query2.png
│   └── mcp-claude-demo.png
├── docker-compose.yml
├── docker-compose.gpu.yml
├── docker-compose.rocm.yml
├── deploy.sh
└── README.md
```

---

## 🧪 Testing

```bash
cd backend
pytest tests/
```

```bash
curl http://localhost:8000/health
```

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"question": "What is Java?"}'
```

```bash
python scripts/evaluate_rag.py
```

---

## 📊 Quality Metrics (RAGAS Evaluated)

Evaluated on **javanotes5.pdf** (699 pages) using **5+ test queries**.

### Results

| Metric             | Score | Target | Status                                   |
|------------------|------|--------|------------------------------------------|
| Answer Relevancy | 1.00 | > 0.8  | ✅ Perfect                                |
| Context Precision| 1.00 | > 0.8  | ✅ Perfect (Re-Ranker Working)            |
| Faithfulness     | 0.67 | > 0.6  | ✅ Pass                                   |
| Context Recall   | 0.67 | > 0.6  | ✅ Pass                                   |

### Notes

> Scores **> 0.6** are considered **production-ready** for technical documentation retrieval.

---

## 🛣️ Roadmap

- [x] MCP Server integration for tool use
- [x] FAISS vector store with ChromaDB fallback
- [x] RAGAS evaluation framework
- [x] Streaming UI with SSE
- [x] Hybrid Search + Re-Ranking
- [ ] Azure AI Search connector
- [ ] Workflow visual builder (Drag & Drop)
- [ ] Advanced Observability (LangSmith/Arize)
- [ ] Kubernetes Helm Charts 

---

## 🤝 Contributing

```bash
git checkout -b feature/your-feature
git commit -m "feat: add feature description"
git push origin feature/your-feature
```

---

## 📄 License

MIT License

---

## 📬 Contact

| Platform | Link |
|----------|------|
| Email | chandansoni44444@gmail.com |
| GitHub | https://github.com/chandankumr |

---

<p align="center">
  🚀 <strong>Build. Orchestrate. Scale AI Systems.</strong>
</p>