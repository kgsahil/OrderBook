# Troubleshooting Guide

Common issues and solutions for the OrderBook trading system.

## Dashboard Issues

### Dashboard stops receiving updates

**Symptoms:**
- Orderbook stops updating
- Chart stops showing new candles
- Agent activity stops appearing

**Solutions:**
1. **Check Connection Status**: Look at the connection indicator in the header
   - Green = Connected
   - Yellow = Connecting
   - Red = Error/Disconnected
   
2. **Manual Reconnect**: Click the "Reconnect" button if shown

3. **Check Browser Console**: Open browser DevTools (F12) and check for errors

4. **Verify OrderBook Service**: Ensure OrderBook is running and accessible
   - Run: `curl http://localhost:8000/health`

5. **Check Network**: Verify WebSocket connection is not blocked by firewall/proxy

**Prevention:**
- Dashboard automatically reconnects with exponential backoff
- Heartbeat monitoring detects stale connections
- Connection status indicator shows current state

### Chart not displaying

**Symptoms:**
- Chart area is blank
- Console shows "LightweightCharts not found"

**Solutions:**
1. **Check Internet Connection**: LightweightCharts loads from CDN
2. **Clear Browser Cache**: Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
3. **Check Console**: Look for JavaScript errors
4. **Verify Chart Container**: Ensure `#priceChart` div exists in HTML

### Performance metrics showing 0

**Symptoms:**
- All metrics show 0 values
- "Error fetching performance metrics" in console

**Solutions:**
1. **Verify Endpoint**: Check if `/api/performance` is accessible
   - Run: `curl http://localhost:8000/api/performance`

2. **Check OrderBook Logs**: Look for errors in OrderBook service
   - Run: `docker logs orderbook`

3. **Verify Router**: Ensure performance router is registered in OrderBook server

## Agent Issues

### Agents not connecting

**Symptoms:**
- "No orderbook received after X seconds" in logs
- Agents terminate immediately

**Solutions:**
1. **Check OrderBook Service**: Ensure OrderBook is running
   - Run: `docker ps | grep orderbook`

2. **Verify WebSocket URL**: Check `WS_URL` environment variable
   - Run: `docker exec agents env | grep WS_URL`

3. **Check Network**: Ensure agents can reach OrderBook
   - Run: `docker exec agents ping orderbook`

4. **Increase Wait Time**: Agents wait up to 10 seconds for initial orderbook data

### Agents not trading

**Symptoms:**
- Agents connect but don't place orders
- No trading activity

**Solutions:**
1. **Check Agent Logs**: Look for decision-making errors
   - Run: `docker logs agents`

2. **Verify Instruments**: Ensure at least one instrument exists
   - Run: `curl http://localhost:8000/api/instruments`

3. **Check Agent Personalities**: Verify personality is valid
   - Valid: `conservative`, `aggressive`, `momentum`, `news_trader`, `market_maker`, `short_seller`, `neutral`, `whale`, `predator`

4. **Check Cash**: Agents need sufficient cash to place orders

### Agents buying at 0 price

**Symptoms:**
- Orders executed at price 0
- Invalid price errors

**Solutions:**
1. **This is now fixed**: Multi-layer validation prevents 0-price orders
2. **If still occurring**: Check OrderBook logs for validation errors
3. **Verify Agent Code**: Ensure agents validate prices before sending orders

## OrderBook Issues

### Orders rejected with "Invalid price"

**Symptoms:**
- Orders fail with price validation errors
- Error: "ERROR Invalid price"

**Solutions:**
1. **Check Order Price**: Ensure price > 0 for LIMIT orders
2. **Verify Price Format**: Price must be a positive number
3. **Check Validation**: Validation occurs at multiple levels:
   - Agent level (before sending)
   - WebSocket server level
   - TCP server level
   - Matching engine level
   - Order book level

### Queue full errors

**Symptoms:**
- "Queue full" messages in logs
- Orders delayed or rejected

**Solutions:**
1. **Check Queue Capacity**: Default is 1024 orders
2. **Monitor Performance Metrics**: Check `queue_usage_pct` in dashboard
3. **Reduce Order Rate**: If agents are sending too many orders too quickly
4. **Increase Capacity**: Modify `DEFAULT_QUEUE_SIZE` in `constants.hpp` (requires rebuild)

### Performance metrics endpoint returns 404

**Symptoms:**
- Dashboard shows "Error fetching performance metrics: 404"
- Metrics endpoint not found

**Solutions:**
1. **Verify Router Registration**: Ensure performance router is included in `server.py`
2. **Check Endpoint Path**: Should be `/api/performance` (not `/performance`)
3. **Restart OrderBook**: Restart the service to register new routes
   - Run: `docker-compose restart orderbook`

## Docker Issues

### Services won't start

**Symptoms:**
- `docker-compose up` fails
- Containers exit immediately

**Solutions:**
1. **Check Logs**: 
   - Run: `docker-compose logs orderbook`, `docker-compose logs dashboard`, `docker-compose logs agents`

2. **Verify Ports**: Ensure ports 8000 and 8080 are not in use
   - Run: `netstat -an | grep -E '8000|8080'`

3. **Check Docker Network**: Ensure services can communicate
   - Run: `docker network ls` and `docker network inspect orderbook_trading-network`

4. **Rebuild Images**: 
   - Run: `docker-compose build --no-cache`

### Services can't communicate

**Symptoms:**
- Connection refused errors
- Services can't reach each other

**Solutions:**
1. **Verify Network**: All services must be on same Docker network
2. **Check Service Names**: Use Docker service names (e.g., `orderbook:8000`, not `localhost:8000`)
3. **Verify Environment Variables**: Check `ORDERBOOK_HOST` and `ORDERBOOK_PORT`
4. **Test Connectivity**: 
   - Run: `docker exec dashboard ping orderbook` and `docker exec agents ping orderbook`

## General Issues

### High memory usage

**Symptoms:**
- System becomes slow
- Out of memory errors

**Solutions:**
1. **Check Container Limits**: Adjust Docker memory limits if needed
2. **Monitor Metrics**: Use dashboard performance metrics
3. **Restart Services**: Periodically restart to clear memory
4. **Check for Leaks**: Review logs for memory-related errors

### Slow performance

**Symptoms:**
- Delayed orderbook updates
- Slow UI response

**Solutions:**
1. **Check System Resources**: CPU, memory, disk I/O
2. **Monitor Network**: Check for network latency
3. **Reduce Load**: Reduce number of agents or order frequency
4. **Check Logs**: Look for performance warnings

## Getting Help

If issues persist:

1. **Check Logs**: Review all service logs
   - Run: `docker-compose logs --tail=100`

2. **Verify Configuration**: Check environment variables and config files

3. **Test Connectivity**: Verify all services can communicate

4. **Review Documentation**: Check [API_REFERENCE.md](API_REFERENCE.md) and [ARCHITECTURE.md](ARCHITECTURE.md)

5. **Create Issue**: Include:
   - Error messages
   - Logs
   - Steps to reproduce
   - System information

