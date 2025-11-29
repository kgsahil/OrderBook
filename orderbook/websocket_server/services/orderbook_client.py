"""Reusable TCP client for communicating with the C++ orderbook."""

from __future__ import annotations

import socket
from typing import Any, Dict


class OrderBookClient:
    """Client to communicate with C++ orderbook backend via TCP."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def _send_raw_command(self, command: str) -> str:
        """Send arbitrary command and return the raw string response."""
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
                bid_count = int(lines[idx].split()[1])
                idx += 1
                for _ in range(bid_count):
                    if idx < len(lines):
                        parts = lines[idx].split()
                        if len(parts) >= 3:
                            bids.append(
                                {
                                    "price": float(parts[0]),
                                    "quantity": float(parts[1]),
                                    "orders": int(parts[2]),
                                }
                            )
                        idx += 1

            if idx < len(lines) and lines[idx].startswith("ASKS"):
                ask_count = int(lines[idx].split()[1])
                idx += 1
                for _ in range(ask_count):
                    if idx < len(lines):
                        parts = lines[idx].split()
                        if len(parts) >= 3:
                            asks.append(
                                {
                                    "price": float(parts[0]),
                                    "quantity": float(parts[1]),
                                    "orders": int(parts[2]),
                                }
                            )
                        idx += 1

            return {"status": "success", "symbol_id": symbol_id, "bids": bids, "asks": asks}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

