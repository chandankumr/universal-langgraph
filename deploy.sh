#!/bin/bash

# Universal LangGraph Platform - One-Click Deploy
# Works on any machine with Docker

set -e

echo "🚀 Universal LangGraph Platform Deployment"
echo "==========================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose found"

# Create directories
mkdir -p data/chroma_db data/logs data/postgres

# Copy environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and set your SECRET_KEY and ENCRYPTION_KEY"
    read -p "Press enter to continue after editing .env..."
fi

# Start services
echo "🔧 Starting services..."
docker-compose up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
echo "🏥 Checking health..."
curl -f http://localhost:8000/health || echo "⚠️  Backend not ready yet"

echo ""
echo "✅ Deployment Complete!"
echo "==========================================="
echo "📍 Frontend: http://localhost:3000"
echo "📍 Backend:  http://localhost:8000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Next Steps:"
echo "1. Open http://localhost:3000 in your browser"
echo "2. Register a new account"
echo "3. Configure your API keys (OpenAI, Anthropic, etc.)"
echo "4. Choose your Vector DB (Chroma, Pinecone, Qdrant, etc.)"
echo "5. Upload documents and start chatting!"
echo ""
echo "🔧 To stop: docker-compose down"
echo "🔧 To view logs: docker-compose logs -f"