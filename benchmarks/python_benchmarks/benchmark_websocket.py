"""Benchmark WebSocket message handling and serialization."""

import json
import pytest
import sys
import os

# Add websocket_server to path
websocket_server_path = os.path.join(os.path.dirname(__file__), '../websocket_server')
if os.path.exists(websocket_server_path):
    sys.path.insert(0, websocket_server_path)
else:
    # Fallback: try absolute path in Docker
    sys.path.insert(0, '/app/websocket_server')

from message_models import OrderPlacedMessage, OrderPlacedPayload, OrderBookMessage


def test_order_message_serialization(benchmark):
    """Benchmark order message JSON serialization."""
    payload = OrderPlacedPayload(
        agent_id="test_agent",
        agent_name="Test Agent",
        symbol_id=1,
        ticker="TEST",
        side="BUY",
        order_type="LIMIT",
        price=10000.0,
        quantity=100,
        timestamp="2025-01-01T00:00:00Z"
    )
    message = OrderPlacedMessage(data=payload)
    
    def serialize():
        return json.dumps(message.model_dump())
    
    result = benchmark(serialize)
    assert isinstance(result, str)
    assert "order_placed" in result


def test_order_message_deserialization(benchmark):
    """Benchmark order message JSON deserialization."""
    json_str = '{"type":"order_placed","version":1,"data":{"agent_id":"test_agent","agent_name":"Test Agent","symbol_id":1,"ticker":"TEST","side":"BUY","order_type":"LIMIT","price":10000.0,"quantity":100,"timestamp":"2025-01-01T00:00:00Z"}}'
    
    def deserialize():
        data = json.loads(json_str)
        return OrderPlacedMessage(**data)
    
    result = benchmark(deserialize)
    assert result.type == "order_placed"
    assert result.data.side == "BUY"


def test_orderbook_message_serialization(benchmark):
    """Benchmark orderbook message JSON serialization."""
    message = OrderBookMessage(
        data={
            1: {
                "bids": [[10000, 100, 1]],
                "asks": [[20000, 100, 1]]
            }
        }
    )
    
    def serialize():
        return json.dumps(message.model_dump())
    
    result = benchmark(serialize)
    assert isinstance(result, str)
    assert "orderbooks" in result


def test_large_message_handling(benchmark):
    """Benchmark handling large orderbook snapshot messages."""
    large_data = {
        "type": "orderbooks",
        "data": {
            "1": {
                "bids": [[10000 + i, 100, 1] for i in range(100)],
                "asks": [[20000 + i, 100, 1] for i in range(100)]
            }
        }
    }
    
    def serialize_deserialize():
        json_str = json.dumps(large_data)
        return json.loads(json_str)
    
    result = benchmark(serialize_deserialize)
    assert result["type"] == "orderbooks"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--benchmark-only'])

