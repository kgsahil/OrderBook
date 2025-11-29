"""Reusable TCP client for communicating with the C++ orderbook.

Supports connection pooling for improved performance and resource management.
"""

from __future__ import annotations

import socket
import threading
import time
from typing import Any, Dict, Optional
from collections import deque


class ConnectionPool:
    """Thread-safe connection pool for TCP connections."""
    
    def __init__(self, host: str, port: int, max_connections: int = 5, 
                 connection_timeout: float = 5.0, idle_timeout: float = 30.0):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout
        self._pool: deque = deque()
        self._lock = threading.Lock()
        self._active_connections = 0
    
    def _create_connection(self) -> Optional[socket.socket]:
        """Create a new TCP connection."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.connection_timeout)
            sock.connect((self.host, self.port))
            return sock
        except Exception:
            return None
    
    def get_connection(self) -> Optional[socket.socket]:
        """Get a connection from the pool or create a new one."""
        with self._lock:
            # Try to get from pool
            while self._pool:
                sock, last_used = self._pool.popleft()
                # Check if connection is still valid and not idle too long
                if time.time() - last_used < self.idle_timeout:
                    try:
                        # Quick check if socket is still valid
                        sock.getpeername()
                        return sock
                    except (OSError, socket.error):
                        # Connection is dead, discard it
                        try:
                            sock.close()
                        except:
                            pass
                        continue
                else:
                    # Connection idle too long, close it
                    try:
                        sock.close()
                    except:
                        pass
            
            # Create new connection if under limit
            if self._active_connections < self.max_connections:
                sock = self._create_connection()
                if sock:
                    self._active_connections += 1
                    return sock
        
        return None
    
    def return_connection(self, sock: Optional[socket.socket]):
        """Return a connection to the pool."""
        if sock is None:
            return
        
        with self._lock:
            try:
                # Check if socket is still valid
                sock.getpeername()
                self._pool.append((sock, time.time()))
            except (OSError, socket.error):
                # Connection is dead, close it
                try:
                    sock.close()
                except:
                    pass
                self._active_connections -= 1
    
    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            while self._pool:
                sock, _ = self._pool.popleft()
                try:
                    sock.close()
                except:
                    pass
            self._active_connections = 0


class OrderBookClient:
    """Client to communicate with C++ orderbook backend via TCP.
    
    Supports connection pooling for improved performance. When pooling is enabled,
    connections are reused across requests, reducing connection overhead.
    """

    def __init__(self, host: str, port: int, use_pooling: bool = True, 
                 max_connections: int = 5, connection_timeout: float = 5.0,
                 retry_attempts: int = 3, retry_delay: float = 0.1):
        self.host = host
        self.port = port
        self.use_pooling = use_pooling
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        if use_pooling:
            self.pool = ConnectionPool(host, port, max_connections, connection_timeout)
        else:
            self.pool = None

    def _send_raw_command(self, command: str) -> str:
        """Send arbitrary command and return the raw string response.
        
        Uses connection pooling if enabled, otherwise creates a new connection per request.
        """
        if self.use_pooling and self.pool:
            return self._send_with_pooling(command)
        else:
            return self._send_without_pooling(command)
    
    def _send_with_pooling(self, command: str) -> str:
        """Send command using connection pool with retry logic."""
        last_error = None
        
        for attempt in range(self.retry_attempts):
            sock = None
            try:
                # Get connection from pool
                sock = self.pool.get_connection()
                if sock is None:
                    if attempt < self.retry_attempts - 1:
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                    return "ERROR Connection pool exhausted\n"
                
                # Send command
                sock.sendall(command.encode() + b"\n")
                
                # Receive response
                response = b""
                sock.settimeout(5.0)  # Response timeout
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if any(marker in response for marker in (b"END\n", b"OK", b"ERROR", b"NOTFOUND")):
                        break
                
                # Return connection to pool
                self.pool.return_connection(sock)
                return response.decode("utf-8", errors="ignore")
                
            except socket.timeout:
                last_error = "Backend timeout"
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                    self.pool.return_connection(None)  # Mark connection as dead
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except (ConnectionRefusedError, OSError) as e:
                last_error = f"Connection error: {e}"
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                    self.pool.return_connection(None)  # Mark connection as dead
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                    self.pool.return_connection(None)
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
        
        return f"ERROR {last_error}\n"
    
    def _send_without_pooling(self, command: str) -> str:
        """Send command without pooling (legacy behavior)."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5.0)
                sock.connect((self.host, self.port))
                sock.sendall(command.encode() + b"\n")

                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if any(marker in response for marker in (b"END\n", b"OK", b"ERROR", b"NOTFOUND")):
                        break

                return response.decode("utf-8", errors="ignore")
        except Exception as exc:
            return f"ERROR {exc}\n"
    
    def close(self):
        """Close all connections in the pool (if pooling is enabled)."""
        if self.pool:
            self.pool.close_all()

    def send_command(self, command: str) -> str:
        """Alias for clarity when called externally."""
        return self._send_raw_command(command)

    def add_order(self, symbol_id: int, side: str, order_type: str, price: float, quantity: float) -> Dict[str, Any]:
        """Add order to orderbook."""
        side_char = "B" if side.upper() == "BUY" else "S"
        type_char = "L" if order_type.upper() == "LIMIT" else "M"
        price_int = int(price) if order_type.upper() == "LIMIT" else 0
        qty_int = int(quantity)

        cmd = f"ADD {symbol_id} {side_char} {type_char} {price_int} {qty_int}"
        response = self._send_raw_command(cmd)

        if response.startswith("OK"):
            parts = response.strip().split()
            order_id = parts[1] if len(parts) > 1 else "0"
            return {"status": "success", "orderId": order_id}
        return {"status": "error", "message": response.strip()}

    def cancel_order(self, symbol_id: int, order_id: int) -> Dict[str, Any]:
        cmd = f"CANCEL {symbol_id} {order_id}"
        response = self._send_raw_command(cmd)
        if response.startswith("OK"):
            return {"status": "success"}
        return {"status": "error", "message": response.strip()}

    def get_snapshot(self, symbol_id: int) -> Dict[str, Any]:
        """Get depth snapshot for an instrument."""
        cmd = f"SNAPSHOT {symbol_id}"
        response = self._send_raw_command(cmd)

        try:
            lines = response.strip().split("\n")
            if not lines or not lines[0].startswith("SNAPSHOT"):
                return {"status": "error", "message": "Invalid response"}

            bids, asks = [], []
            idx = 1

            if idx < len(lines) and lines[idx].startswith("BIDS"):
                try:
                    bid_count = int(lines[idx].split()[1])
                except (IndexError, ValueError):
                    return {"status": "error", "message": "Invalid BIDS header format"}
                idx += 1
                for _ in range(bid_count):
                    if idx >= len(lines):
                        break  # Prevent index out of bounds
                    parts = lines[idx].split()
                    if len(parts) >= 3:
                        try:
                            bids.append(
                                {
                                    "price": float(parts[0]),
                                    "quantity": float(parts[1]),
                                    "orders": int(parts[2]),
                                }
                            )
                        except (ValueError, IndexError):
                            # Skip malformed line
                            pass
                    idx += 1

            if idx < len(lines) and lines[idx].startswith("ASKS"):
                try:
                    ask_count = int(lines[idx].split()[1])
                except (IndexError, ValueError):
                    return {"status": "error", "message": "Invalid ASKS header format"}
                idx += 1
                for _ in range(ask_count):
                    if idx >= len(lines):
                        break  # Prevent index out of bounds
                    parts = lines[idx].split()
                    if len(parts) >= 3:
                        try:
                            asks.append(
                                {
                                    "price": float(parts[0]),
                                    "quantity": float(parts[1]),
                                    "orders": int(parts[2]),
                                }
                            )
                        except (ValueError, IndexError):
                            # Skip malformed line
                            pass
                    idx += 1

            return {"status": "success", "symbol_id": symbol_id, "bids": bids, "asks": asks}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

