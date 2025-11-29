"""Service for managing instruments."""

from typing import Dict, List, Optional

from models.instrument import Instrument
from .orderbook_client import OrderBookClient


class InstrumentService:
    """Manages instrument registry and communication with C++ backend."""
    
    def __init__(self, client: Optional[OrderBookClient] = None, cpp_host: str = "localhost", cpp_port: int = 9999):
        self.client = client or OrderBookClient(cpp_host, cpp_port)
        self.instruments: Dict[int, Instrument] = {}
    
    def _send_command(self, command: str) -> str:
        """Send command to C++ backend and get response."""
        return self.client.send_command(command)
    
    def add_instrument(self, ticker: str, description: str, industry: str, initial_price: float) -> Optional[Instrument]:
        """Add a new instrument."""
        # Escape pipe characters in fields
        ticker_escaped = ticker.replace('|', '_')
        desc_escaped = description.replace('|', '_')
        industry_escaped = industry.replace('|', '_')
        price_str = f"{initial_price:.2f}"
        
        cmd = f"ADD_INSTRUMENT {ticker_escaped}|{desc_escaped}|{industry_escaped}|{price_str}"
        response = self._send_command(cmd)
        
        if response.startswith("OK"):
            parts = response.strip().split()
            symbol_id = int(parts[1])
            
            instrument = Instrument(
                symbol_id=symbol_id,
                ticker=ticker,
                description=description,
                industry=industry,
                initial_price=initial_price,
                created_at=None  # Will be set by C++ backend
            )
            self.instruments[symbol_id] = instrument
            return instrument
        return None
    
    def remove_instrument(self, symbol_id: int) -> bool:
        """Remove an instrument."""
        cmd = f"REMOVE_INSTRUMENT {symbol_id}"
        response = self._send_command(cmd)
        
        if response.startswith("OK"):
            self.instruments.pop(symbol_id, None)
            return True
        return False
    
    def list_instruments(self) -> List[Instrument]:
        """List all instruments."""
        cmd = "LIST_INSTRUMENTS"
        response = self._send_command(cmd)
        
        instruments = []
        try:
            lines = response.strip().split('\n')
            if not lines or not lines[0].startswith("INSTRUMENTS"):
                return list(self.instruments.values())
            
            # Parse response
            for line in lines[1:]:
                if line == "END":
                    break
                parts = line.split('|')
                if len(parts) >= 4:
                    symbol_id = int(parts[0])
                    ticker = parts[1]
                    description = parts[2]
                    industry = parts[3]
                    initial_price = 0.0
                    if len(parts) >= 5:
                        try:
                            initial_price = float(parts[4])
                        except ValueError:
                            initial_price = 0.0
                    
                    instrument = Instrument(
                        symbol_id=symbol_id,
                        ticker=ticker,
                        description=description,
                        industry=industry,
                        initial_price=initial_price,
                        created_at=None
                    )
                    self.instruments[symbol_id] = instrument
                    instruments.append(instrument)
        except Exception as e:
            print(f"Error parsing instruments: {e}")
        
        return list(self.instruments.values())
    
    def get_instrument(self, symbol_id: int) -> Optional[Instrument]:
        """Get instrument by symbol ID."""
        return self.instruments.get(symbol_id)
    
    def has_instrument(self, symbol_id: int) -> bool:
        """Check if instrument exists."""
        return symbol_id in self.instruments

