# Agents Component

AI trading agents that connect to OrderBook and make trading decisions using a layered pipeline of **LLMs** (optional), **ML models**, and **statistical heuristic strategies**.

## Architecture

- **LangGraph Agents (optional)**: LLM-based decision making and reasoning (only used when an API key is provided)
- **Strategy Module**: Configurable heuristic, ML, and personality-based strategies (see `agents/strategies/README.md`)
- **WebSocket Client**: Connects to OrderBook WebSocket API
- **Multiple Agents**: Configurable number of agents with different personalities and risk profiles

## Ports

- **None**: Agents connect to OrderBook, no exposed ports

## Configuration

See `config/agent_config.yaml` for agent configuration (number of agents, personalities, ML usage, etc.).

**Environment Variables (connectivity & LLM):**
- `WS_URL`: OrderBook WebSocket URL (default: `ws://orderbook:8000/ws`)
- `GOOGLE_API_KEY`: Google Gemini API key
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `LLM_PROVIDER`: LLM provider (default: `gemini`)
- `LLM_MODEL`: Model name (default: `gemini-2.0-flash-exp`)
- `MAX_RETRIES`: Connection retry attempts (default: `5`)
- `RETRY_DELAY`: Retry delay in seconds (default: `5`)

**Strategy / ML toggles (configured via env or YAML, depending on your setup):**
- Enable/disable **ML-backed strategies** (RandomForest-based signals)
- Switch between **pure heuristic**, **pure ML**, or **hybrid personality** strategies
- Choose personality profiles (e.g. conservative, aggressive, market-maker, news-trader, momentum)

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
- Agents make trading decisions based on orderbook state, instruments, and news
- **LLM usage is strictly opt‑in**:
  - If a valid LLM API key is provided, agents can use LLM calls for higher-level reasoning and commentary.
  - If **no LLM/API key** is provided, agents **do not** call any LLMs.
- **Fallback chain** when placing trades (see `agents/strategies/README.md`):
  1. Try **ML strategy** (RandomForest model) when enabled and confident enough.
  2. If ML is disabled or not confident, use **statistical heuristic strategy** (rule-based, personality-aware).

## Dependencies

- Python 3.10+
- LangGraph, LangChain, LLM provider SDKs
- websockets
- scikit-learn / numpy (for ML strategies, see `agents/strategies/README.md`)

## External Dependencies

Requires OrderBook service to be running and accessible. Agents will terminate if OrderBook is unavailable.
