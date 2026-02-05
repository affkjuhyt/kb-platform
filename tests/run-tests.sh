#!/bin/bash
# Run all tests for RAG Platform
# Usage: ./run-tests.sh [smoke|e2e|postman|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default: run smoke test
TEST_TYPE="${1:-smoke}"

echo "🧪 RAG Platform Test Runner"
echo "============================"
echo ""

case "$TEST_TYPE" in
  smoke)
    echo "🔥 Running Smoke Test..."
    echo ""
    uv run python smoke_test.py
    ;;
  
  e2e)
    echo "🔄 Running E2E Tests..."
    echo ""
    uv run pytest e2e/ -v --tb=short
    ;;
  
  postman)
    echo "📮 Running Postman Collection..."
    echo ""
    if ! command -v newman &> /dev/null; then
      echo "❌ Newman not found. Install with: npm install -g newman"
      exit 1
    fi
    
    newman run postman/rag-platform.json \
      --env-var "base_url=http://localhost:8080" \
      --env-var "ingestion_url=http://localhost:8001" \
      --env-var "query_url=http://localhost:8003" \
      --env-var "llm_url=http://localhost:8004" \
      --env-var "rerank_url=http://localhost:8005" \
      --reporters cli
    ;;
  
  all)
    echo "🚀 Running All Tests..."
    echo ""
    
    echo "1️⃣ Smoke Test"
    uv run python smoke_test.py
    
    echo ""
    echo "2️⃣ E2E Tests"
    uv run pytest e2e/ -v --tb=short
    
    echo ""
    echo "3️⃣ Postman Collection"
    if command -v newman &> /dev/null; then
      newman run postman/rag-platform.json \
        --env-var "base_url=http://localhost:8080" \
        --env-var "ingestion_url=http://localhost:8001" \
        --env-var "query_url=http://localhost:8003" \
        --env-var "llm_url=http://localhost:8004" \
        --env-var "rerank_url=http://localhost:8005" \
        --reporters cli
    else
      echo "⚠️  Newman not found, skipping Postman tests"
    fi
    ;;
  
  *)
    echo "Usage: ./run-tests.sh [smoke|e2e|postman|all]"
    echo ""
    echo "Commands:"
    echo "  smoke   - Quick health check (30s)"
    echo "  e2e     - Full E2E tests"
    echo "  postman - Run Postman collection via Newman"
    echo "  all     - Run everything"
    exit 1
    ;;
esac

echo ""
echo "✅ Tests completed!"
