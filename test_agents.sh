#!/bin/bash
# Test script to verify agents are working correctly
# Can be run from host or inside Docker

echo "============================================================"
echo "Agent Testing Script"
echo "============================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in Docker or on host
if [ -f /.dockerenv ]; then
    WS_URL="ws://orderbook:8000/ws"
    API_URL="http://orderbook:8000/api"
else
    WS_URL="ws://localhost:8000/ws"
    API_URL="http://localhost:8000/api"
fi

echo ""
echo "1. Checking OrderBook connection..."
if curl -s -f "${API_URL%/api}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OrderBook is accessible${NC}"
else
    echo -e "${RED}✗ Cannot connect to OrderBook${NC}"
    exit 1
fi

echo ""
echo "2. Checking agents via API..."
AGENTS_RESPONSE=$(curl -s "${API_URL}/agents" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$AGENTS_RESPONSE" ]; then
    AGENT_COUNT=$(echo "$AGENTS_RESPONSE" | grep -o '"name"' | wc -l)
    if [ "$AGENT_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $AGENT_COUNT agent(s)${NC}"
        echo "$AGENTS_RESPONSE" | python3 -m json.tool 2>/dev/null | head -20
    else
        echo -e "${YELLOW}⚠ No agents found via API${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Could not fetch agents from API${NC}"
fi

echo ""
echo "3. Checking agent container logs (last 20 lines)..."
if command -v docker &> /dev/null; then
    if docker ps | grep -q agents-service; then
        echo "Recent agent logs:"
        docker logs --tail 20 agents-service 2>&1 | grep -E "(Connected|decision|order|Agent_|Fallback|Using heuristic)" | tail -10
        echo ""
        echo "Checking for errors..."
        ERROR_COUNT=$(docker logs agents-service 2>&1 | grep -i "error\|exception\|traceback" | wc -l)
        if [ "$ERROR_COUNT" -gt 0 ]; then
            echo -e "${YELLOW}⚠ Found $ERROR_COUNT error(s) in logs${NC}"
            docker logs agents-service 2>&1 | grep -i "error\|exception" | tail -5
        else
            echo -e "${GREEN}✓ No recent errors found${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Agents container not running${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Docker not available, skipping log check${NC}"
fi

echo ""
echo "4. Checking for trading activity..."
if command -v docker &> /dev/null; then
    if docker ps | grep -q agents-service; then
        TRADE_ACTIVITY=$(docker logs agents-service 2>&1 | grep -i "placed\|order\|trade\|BUY\|SELL" | tail -5)
        if [ -n "$TRADE_ACTIVITY" ]; then
            echo -e "${GREEN}✓ Found trading activity:${NC}"
            echo "$TRADE_ACTIVITY"
        else
            echo -e "${YELLOW}⚠ No recent trading activity found${NC}"
        fi
    fi
fi

echo ""
echo "5. Checking orderbook for liquidity..."
INSTRUMENTS=$(curl -s "${API_URL}/instruments" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$INSTRUMENTS" ]; then
    INST_COUNT=$(echo "$INSTRUMENTS" | grep -o '"symbol_id"' | wc -l)
    echo -e "${GREEN}✓ Found $INST_COUNT instrument(s)${NC}"
    
    # Check if orderbooks have liquidity (this would require WebSocket, simplified here)
    echo "  (Use dashboard to check orderbook liquidity)"
else
    echo -e "${YELLOW}⚠ Could not fetch instruments${NC}"
fi

echo ""
echo "============================================================"
echo "Test Summary"
echo "============================================================"
echo "To verify agents are working:"
echo "1. Check dashboard at http://localhost:8080"
echo "2. Look for agent activity in the Agents tab"
echo "3. Check orderbook for trading activity"
echo "4. Monitor agent logs: docker logs -f agents-service"
echo "============================================================"

