"""Benchmark TCP client connection pooling and message handling."""

import time
import socket
import threading
import pytest
from concurrent.futures import ThreadPoolExecutor
import sys
import os
import random

# Import orderbook_client directly to avoid services/__init__.py dependencies
import importlib.util

# Try to find the orderbook_client module
websocket_server_path = os.path.join(os.path.dirname(__file__), '../websocket_server')
if not os.path.exists(websocket_server_path):
    websocket_server_path = '/app/websocket_server'

orderbook_client_path = os.path.join(websocket_server_path, 'services', 'orderbook_client.py')
if os.path.exists(orderbook_client_path):
    spec = importlib.util.spec_from_file_location("orderbook_client", orderbook_client_path)
    orderbook_client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(orderbook_client)
    OrderBookClient = orderbook_client.OrderBookClient
    ConnectionPool = orderbook_client.ConnectionPool
else:
    # Fallback: try normal import
    sys.path.insert(0, websocket_server_path)
    from services.orderbook_client import OrderBookClient, ConnectionPool


class MockTCPServer:
    """Mock TCP server for benchmarking."""
    
    def __init__(self, host='localhost', port=None):
        self.host = host
        # Use a random port to avoid conflicts
        if port is None:
            # Find an available port
            self.port = self._find_free_port()
        else:
            self.port = port
        self.sock = None
        self.running = False
        self.thread = None
    
    def _find_free_port(self):
        """Find a free port."""
        for _ in range(10):  # Try up to 10 times
            port = random.randint(10000, 65535)
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.bind(('', port))
                test_sock.close()
                return port
            except OSError:
                continue
        raise RuntimeError("Could not find a free port")
    
    def start(self):
        """Start mock server."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        self.running = True
        
        def handle_client(client_sock):
            while self.running:
                try:
                    data = client_sock.recv(4096)
                    if not data:
                        break
                    # Echo back response
                    client_sock.send(b"OK 12345\n")
                except:
                    break
            client_sock.close()
        
        def accept_loop():
            while self.running:
                try:
                    client, _ = self.sock.accept()
                    threading.Thread(target=handle_client, args=(client,), daemon=True).start()
                except:
                    break
        
        self.thread = threading.Thread(target=accept_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop mock server."""
        self.running = False
        if self.sock:
            self.sock.close()


@pytest.fixture
def mock_server():
    """Fixture for mock TCP server."""
    # Use a random port to avoid conflicts
    server = MockTCPServer()
    server.start()
    yield server
    server.stop()


def test_connection_pool_get_return(benchmark, mock_server):
    """Benchmark connection pool get/return operations."""
    pool = ConnectionPool('localhost', mock_server.port, max_connections=5)
    
    def get_return_cycle():
        sock = pool.get_connection()
        if sock:
            pool.return_connection(sock)
        return sock is not None
    
    result = benchmark(get_return_cycle)
    assert result
    
    pool.close_all()


def test_tcp_client_with_pooling(benchmark, mock_server):
    """Benchmark TCP client with connection pooling."""
    client = OrderBookClient('localhost', mock_server.port, use_pooling=True, max_connections=5)
    
    def send_command():
        return client._send_raw_command("SNAPSHOT 1")
    
    result = benchmark(send_command)
    assert result.startswith("OK")
    
    client.close()


def test_tcp_client_without_pooling(benchmark, mock_server):
    """Benchmark TCP client without connection pooling."""
    client = OrderBookClient('localhost', mock_server.port, use_pooling=False)
    
    def send_command():
        return client._send_raw_command("SNAPSHOT 1")
    
    result = benchmark(send_command)
    assert result.startswith("OK")
    
    client.close()


def test_concurrent_requests(benchmark, mock_server):
    """Benchmark concurrent TCP requests."""
    client = OrderBookClient('localhost', mock_server.port, use_pooling=True, max_connections=10)
    
    def concurrent_requests():
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(client._send_raw_command, f"SNAPSHOT {i}") 
                      for i in range(100)]
            results = [f.result() for f in futures]
        return len(results)
    
    result = benchmark(concurrent_requests)
    assert result == 100
    
    client.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--benchmark-only'])

