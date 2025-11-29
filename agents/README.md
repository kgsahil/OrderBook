# Agents Component

AI trading agents that connect to OrderBook and make trading decisions using LLMs.

## Architecture

- **LangGraph Agents**: LLM-based decision making
- **WebSocket Client**: Connects to OrderBook WebSocket API
- **Multiple Agents**: Configurable number of agents with different personalities

## Ports

- **None**: Agents connect to OrderBook, no exposed ports

## Configuration

See `config/agent_config.yaml` for agent configuration.

**Environment Variables:**
- `WS_URL`: OrderBook WebSocket URL (default: `ws://orderbook:8000/ws`)
- `GOOGLE_API_KEY`: Google Gemini API key
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `LLM_PROVIDER`: LLM provider (default: `gemini`)
- `LLM_MODEL`: Model name (default: `gemini-2.0-flash-exp`)
- `MAX_RETRIES`: Connection retry attempts (default: `5`)
- `RETRY_DELAY`: Retry delay in seconds (default: `5`)

## Building

```bash
docker build -t agents-service -f Dockerfile .
```

## Running

```bash
docker run \
  -e GOOGLE_API_KEY=your_key \
  -e WS_URL=ws://orderbook:8000/ws \
  agents-service
```

Or via docker-compose:

```bash
export GOOGLE_API_KEY=your_key
docker-compose up agents
```

## Behavior

- Agents connect to OrderBook on startup
- If connection fails after `MAX_RETRIES`, agents terminate
- Agents register via WebSocket and receive real-time orderbook updates
- Agents make trading decisions based on orderbook state and news

## Dependencies

- Python 3.10+
- LangGraph, LangChain, LLM provider SDKs
- websockets

## External Dependencies

Requires OrderBook service to be running and accessible. Agents will terminate if OrderBook is unavailable.
