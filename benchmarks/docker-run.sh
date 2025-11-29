#!/bin/bash

# Docker-based benchmark runner
# This script runs benchmarks against the running OrderBook services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "🚀 OrderBook Docker Benchmarks"
echo "==============================="
echo ""

# Check if services are running
echo "📡 Checking services..."
if ! docker-compose ps | grep -q "orderbook-service.*Up"; then
    echo "❌ OrderBook service is not running!"
    echo "   Please start services first: docker-compose up -d"
    exit 1
fi

echo "✅ Services are running"
echo ""

# Build benchmark image if not exists
echo "🔨 Building benchmark image..."
docker-compose build benchmarks

# Run benchmarks
echo ""
echo "⚡ Running benchmarks..."
docker-compose run --rm benchmarks

# Copy results from container
echo ""
echo "📊 Copying results..."
CONTAINER_ID=$(docker-compose run -d --rm benchmarks)
docker cp ${CONTAINER_ID}:/app/results ./benchmarks/results/ 2>/dev/null || true
docker stop ${CONTAINER_ID} >/dev/null 2>&1 || true

echo ""
echo "✅ Benchmarks complete! Results saved to benchmarks/results/"

