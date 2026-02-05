#!/bin/bash
# Start all services cho development/testing
# Bao gồm cả LLM Gateway (mock) và Rerank

set -e

echo "🚀 Starting RAG Platform Services..."
echo ""

cd "$(dirname "$0")"

# Check if docker-compose or docker compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "❌ Docker Compose not found"
    exit 1
fi

echo "📦 Starting core services..."
$COMPOSE_CMD up -d

echo ""
echo "📦 Starting dev services (LLM Mock + Rerank)..."
$COMPOSE_CMD -f docker-compose.dev.yml up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

echo ""
echo "✅ Services started!"
echo ""
echo "📊 Access URLs:"
echo "  - API Gateway:    http://localhost:8080"
echo "  - Ingestion:      http://localhost:8001"
echo "  - Indexer:        http://localhost:8002"
echo "  - Query API:      http://localhost:8003"
echo "  - LLM Gateway:    http://localhost:8004 (mock)"
echo "  - Rerank:         http://localhost:8005"
echo "  - OpenSearch:     http://localhost:9200"
echo "  - Qdrant:         http://localhost:6333"
echo "  - MinIO Console:  http://localhost:9001"
echo "  - Grafana:        http://localhost:3000"
echo ""
echo "🧪 Run smoke test:"
echo "  python tests/smoke_test.py"
