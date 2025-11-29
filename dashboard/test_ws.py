import asyncio
import websockets
import sys

async def test_connection():
    uri = "ws://orderbook:8000/ws"
    print(f"Testing connection to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Successfully connected!")
            await websocket.close()
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(test_connection())
    except ImportError:
        print("Error: websockets library not found")
        sys.exit(1)
