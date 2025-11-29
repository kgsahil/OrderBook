#!/bin/bash

echo "======================================"
echo "  OrderBook Trading System - Docker  "
echo "======================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose found"
echo ""

# Build and start OrderBook
echo "🔨 Building and starting OrderBook container..."
docker-compose up -d --build orderbook

# Wait for OrderBook to be healthy
echo "⏳ Waiting for OrderBook to be ready..."
sleep 5

# Check if OrderBook is healthy
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ OrderBook is running!"
    echo ""
    
    # Start Dashboard
    echo "📊 Starting Dashboard..."
    docker-compose up -d dashboard
    echo "✅ Dashboard started!"
    echo ""
    
    # Check if user wants to start agents
    if [ -n "$GOOGLE_API_KEY" ] || [ -n "$OPENAI_API_KEY" ] || [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "🤖 Starting AI agents..."
        docker-compose up -d agents
        echo "✅ Agents started!"
    else
        echo "💡 To start agents, set GOOGLE_API_KEY and run:"
        echo "   docker-compose up -d agents"
    fi
    
    echo ""
    echo "📊 Access the admin dashboard at:"
    echo "   http://localhost:8080"
    echo ""
    echo "📋 Useful commands:"
    echo "   docker-compose logs -f          # View all logs"
    echo "   docker-compose logs -f agents  # View agent logs"
    echo "   docker-compose down             # Stop all containers"
    echo "   docker-compose ps               # Check status"
    echo ""
    echo "Opening browser in 3 seconds..."
    sleep 3
    
    # Try to open browser (works on most Linux systems)
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8080
    elif command -v gnome-open &> /dev/null; then
        gnome-open http://localhost:8080
    else
        echo "Please open http://localhost:8080 in your browser"
    fi
else
    echo ""
    echo "❌ OrderBook failed to start"
    echo "Check logs with: docker-compose logs orderbook"
    exit 1
fi

