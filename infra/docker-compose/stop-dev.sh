#!/bin/bash
# Stop all services

set -e

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

echo "🛑 Stopping all services..."
$COMPOSE_CMD -f docker-compose.yml -f docker-compose.dev.yml down

echo ""
echo "✅ All services stopped"
