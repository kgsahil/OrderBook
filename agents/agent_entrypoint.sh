#!/bin/bash
# Entrypoint script for agent container
# Connects to OrderBook service and terminates if connection fails

set -e

WS_URL=${WS_URL:-"ws://orderbook:8000/ws"}
MAX_RETRIES=${MAX_RETRIES:-5}
RETRY_DELAY=${RETRY_DELAY:-5}
CONFIG_FILE=${CONFIG_FILE:-"/app/config/agent_config.yaml"}

echo "=========================================="
echo "AI Trading Agents Container"
echo "=========================================="
echo "WebSocket URL: $WS_URL"
echo "Max Retries: $MAX_RETRIES"
echo "Retry Delay: ${RETRY_DELAY}s"
echo ""

# Function to check if OrderBook is reachable
check_orderbook() {
    # Extract host and port from WS_URL
    HOST=$(echo $WS_URL | sed -E 's|ws://([^:]+):([0-9]+)/.*|\1|')
    PORT=$(echo $WS_URL | sed -E 's|ws://([^:]+):([0-9]+)/.*|\2|')
    
    echo "Checking connection to $HOST:$PORT..."
    
    # Try to connect to HTTP endpoint first (health check)
    HTTP_URL="http://${HOST}:${PORT}/health"
    
    if curl -f -s --max-time 5 "$HTTP_URL" > /dev/null 2>&1; then
        echo "✓ OrderBook is reachable"
        return 0
    else
        echo "✗ Cannot reach OrderBook"
        return 1
    fi
}

# Retry logic
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if check_orderbook; then
        echo ""
        echo "Starting agents..."
        echo ""
        
        # Update config with WS_URL if needed
        if [ -f "$CONFIG_FILE" ]; then
            # Use sed to update ws_url in config if it exists
            # Handle both with and without quotes
            sed -i "s|ws_url:.*|ws_url: \"$WS_URL\"|" "$CONFIG_FILE" 2>/dev/null || true
            echo "Updated config: ws_url = $WS_URL"
        fi
        
        # Start agents
        cd /app/agents
        python3 run_agents.py "$CONFIG_FILE"
        exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            echo "Agents stopped normally"
            exit 0
        else
            echo "Agents exited with error code: $exit_code"
            exit $exit_code
        fi
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "Retry $RETRY_COUNT/$MAX_RETRIES in ${RETRY_DELAY}s..."
            sleep $RETRY_DELAY
        else
            echo ""
            echo "=========================================="
            echo "ERROR: Failed to connect to OrderBook"
            echo "=========================================="
            echo "Attempted $MAX_RETRIES times"
            echo "WebSocket URL: $WS_URL"
            echo ""
            echo "Please ensure:"
            echo "  1. OrderBook container is running"
            echo "  2. WebSocket server is accessible at $WS_URL"
            echo "  3. Network connectivity between containers"
            echo ""
            exit 1
        fi
    fi
done

