#!/bin/bash
# Quick Start Script for Ingestion Service

set -e

echo "=========================================="
echo "Ingestion Service - Quick Start"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q -r requirements.txt

# Check if infrastructure is running
echo -e "${YELLOW}Checking infrastructure services...${NC}"

if curl -s http://localhost:5432 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not running on port 5432${NC}"
    echo "Start it with: docker-compose up -d postgres"
    exit 1
fi

if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MinIO is running${NC}"
else
    echo -e "${RED}✗ MinIO is not running on port 9000${NC}"
    echo "Start it with: docker-compose up -d minio"
    exit 1
fi

if nc -z localhost 9092 2>/dev/null; then
    echo -e "${GREEN}✓ Kafka is running${NC}"
else
    echo -e "${YELLOW}⚠ Kafka is not running on port 9092 (optional)${NC}"
fi

# Set environment variables
export RAG_SERVICE_PORT=8002
export RAG_POSTGRES_DSN="postgresql://rag:rag@localhost:5432/rag"
export RAG_MINIO_ENDPOINT="localhost:9000"
export RAG_MINIO_ACCESS_KEY="minio"
export RAG_MINIO_SECRET_KEY="minio123"
export RAG_MINIO_BUCKET="raw-docs"
export RAG_KAFKA_BROKERS="localhost:9092"
export RAG_KAFKA_TOPIC="ingestion.events"

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
python3 -c "from migrations import run_migrations; run_migrations()"

# Ensure MinIO bucket exists
echo -e "${YELLOW}Ensuring MinIO bucket exists...${NC}"
python3 -c "from storage import storage_service_factory; storage_service_factory().ensure_bucket()"

# Start service
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}Starting Ingestion Service on port 8002...${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo "Health check: http://localhost:8002/healthz"
echo "Webhook:      http://localhost:8002/webhook"
echo "Pull:         http://localhost:8002/pull"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 -m uvicorn app:app --host 0.0.0.0 --port 8002 --reload