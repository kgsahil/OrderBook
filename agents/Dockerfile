# syntax=docker/dockerfile:1.4
# Dockerfile for AI Agents component
FROM ubuntu:22.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file first (for better Docker layer caching)
# This layer will be cached unless requirements.txt changes
COPY agents/requirements.txt ./requirements.txt

# Upgrade pip and install dependencies
# Use BuildKit cache mount for pip cache (faster rebuilds)
# Syntax: --mount=type=cache,target=/root/.cache/pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install --upgrade pip setuptools wheel && \
    pip3 install --timeout=60 -r requirements.txt

# Copy agent code (this changes more frequently, so it's after dependencies)
COPY agents/ ./agents/
COPY agents/config/ ./config/
COPY agents/agent_entrypoint.sh ./agent_entrypoint.sh

# Make entrypoint executable
RUN chmod +x /app/agent_entrypoint.sh

# Default environment variables
ENV WS_URL=ws://orderbook:8000/ws
ENV MAX_RETRIES=5
ENV RETRY_DELAY=5
ENV START_AGENTS=true

# Run agents
ENTRYPOINT ["/app/agent_entrypoint.sh"]

