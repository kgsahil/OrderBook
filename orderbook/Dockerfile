# Multi-stage Dockerfile for OrderBook component
# Stage 1: Build C++ orderbook backend
FROM ubuntu:22.04 AS cpp-builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy C++ source code
WORKDIR /build
COPY CMakeLists.txt ./
COPY include/ ./include/
COPY src/ ./src/
COPY apps/ ./apps/

# Build the C++ orderbook server
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    -DORDERBOOK_ENABLE_SANITIZERS=OFF \
    && cmake --build build --parallel --target ob_server

# Stage 2: Runtime image
FROM ubuntu:22.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy C++ binary from builder
COPY --from=cpp-builder /build/build/ob_server /app/ob_server

# Copy Python WebSocket server
WORKDIR /app
COPY websocket_server/ ./websocket_server/

# Install WebSocket server dependencies
RUN pip3 install --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir --timeout=60 -r websocket_server/requirements.txt

# Create supervisor configuration
RUN mkdir -p /var/log/supervisor
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create directories for logs
RUN mkdir -p /var/log/supervisor /app/logs

# Expose WebSocket server port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run all services via supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

