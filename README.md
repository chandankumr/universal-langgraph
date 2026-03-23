# 🌐 Universal LangGraph AI Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/FastAPI-Production-green?style=for-the-badge&logo=fastapi" />
  <img src="https://img.shields.io/badge/LangGraph-Agentic_AI-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Azure_OpenAI-Supported-0078D4?style=for-the-badge&logo=microsoft-azure" />
  <img src="https://img.shields.io/badge/RAG-Pipeline-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Docker-Kubernetes-red?style=for-the-badge&logo=docker" />
  <img src="https://img.shields.io/badge/License-MIT-purple?style=for-the-badge" />
</p>

<p align="center">
  <strong>Enterprise-Ready Agentic AI Platform with Multi-Agent Workflows, RAG, and Azure Integration</strong>
</p>

---

## 🚀 Overview

A **production-grade agentic AI orchestration platform** built for enterprise deployment.
Designed to execute **autonomous multi-agent workflows** with Retrieval-Augmented Generation (RAG).

Supports:

* Multiple LLM providers (Azure OpenAI, OpenAI, Google, Ollama)
* Multiple vector databases (Chroma, Pinecone, Qdrant)

---

## 🏆 Key Highlights

| Feature               | Implementation                                                       | Enterprise Value               |
| --------------------- | -------------------------------------------------------------------- | ------------------------------ |
| Multi-Agent Workflows | LangGraph with routing, retrieval, generation, self-correction nodes | Automates complex workflows    |
| RAG Pipeline          | Multi-vector DB support                                              | Enterprise knowledge retrieval |
| LLM Flexibility       | Azure, OpenAI, Google, Ollama                                        | Cost optimization & privacy    |
| Security              | JWT auth, encrypted API keys                                         | Production-ready security      |
| Deployment            | Docker, GPU support (NVIDIA/AMD)                                     | Scalable infrastructure        |
| Monitoring            | Token analytics, logging                                             | Observability                  |

---

## 🏗️ System Architecture

```
Client (UI)
     │
     ▼
FastAPI Backend
(Auth, APIs, Validation)
     │
     ▼
LangGraph Engine
(Router → Retrieve → Generate → Critic)
     │
 ┌───┴───────────────┐
 ▼                   ▼
Vector DBs        LLM Providers
(Chroma, etc.)    (OpenAI, Ollama, etc.)
```

---

## ⚙️ Features

### 🤖 Agentic AI Workflows

* Multi-agent orchestration using LangGraph
* Intelligent routing & query classification
* Self-correction loops (critic nodes)
* Multi-step reasoning workflows
* Memory with conversation history

### 🔍 RAG Pipeline

* ChromaDB, Pinecone, Qdrant support
* Document ingestion (PDF, TXT, DOCX, MD)
* Chunking + embeddings
* Semantic search

### 🔌 Model-Agnostic Inference

* Azure OpenAI
* OpenAI
* Google Gemini
* Ollama (local models)

### 🔐 Security

* JWT authentication
* API key encryption
* Multi-tenant isolation
* Audit logging

### 🚀 Deployment

* Docker-based setup
* CPU / NVIDIA GPU / AMD ROCm support

---

## ⚙️ Quick Start

### Prerequisites

* Docker & Docker Compose
* Python 3.11+
* Git

---

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/universal-langgraph.git
cd universal-langgraph
```

---

### 2. Configure Environment

```bash
cd backend
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=your_key_here
# OR
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

---

### 3. Deploy

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

---

### 4. Access Services

| Service     | URL                        |
| ----------- | -------------------------- |
| Frontend    | http://localhost:3000      |
| Backend API | http://localhost:8000      |
| API Docs    | http://localhost:8000/docs |

---

## 📁 Project Structure

```
backend/
  ├── app/
  │   ├── graphs/
  │   ├── services/
  │   ├── main.py
  │   └── auth.py
frontend/
docker-compose.yml
README.md
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

---

## 🛣️ Roadmap

* MCP Server integration
* Azure AI Search
* Workflow visual builder
* Observability & tracing
* Kubernetes deployment

---

## 🤝 Contributing

```bash
git checkout -b feature/your-feature
git commit -m "Add feature"
git push origin feature/your-feature
```

---

## 📄 License

MIT License

---

## 📬 Contact

* Email: [chandansoni44444@gmail.com](mailto:chandansoni44444@gmail.com)
* GitHub: https://github.com/chandankumr

---

<p align="center">
  🚀 <em>Build. Orchestrate. Scale AI Systems with Confidence.</em>
</p>
