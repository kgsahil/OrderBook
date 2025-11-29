# Multi-stage Dockerfile for OrderBook Benchmarks
# Stage 1: Build C++ benchmarks
FROM ubuntu:22.04 AS cpp-builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy benchmark source code
WORKDIR /build
COPY benchmarks/CMakeLists.txt ./
COPY benchmarks/cpp/ ./cpp/

# Copy orderbook source (needed for building)
COPY orderbook/CMakeLists.txt ./orderbook/
COPY orderbook/include/ ./orderbook/include/
COPY orderbook/src/ ./orderbook/src/

# Build benchmarks
# Note: CMakeLists.txt expects orderbook at ../orderbook relative to benchmarks
RUN mkdir -p ../orderbook && \
    cp -r orderbook/* ../orderbook/ && \
    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
        -DBENCHMARK_DOWNLOAD_DEPENDENCIES=ON \
        -DBENCHMARK_ENABLE_GTEST_TESTS=OFF \
    && cmake --build build --parallel

# Stage 2: Runtime image with Python and C++ benchmarks
FROM ubuntu:22.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy C++ benchmarks from builder
COPY --from=cpp-builder /build/build/benchmarks /app/benchmarks

# Copy Python benchmarks
WORKDIR /app
COPY benchmarks/python_benchmarks/ ./python_benchmarks/
# Copy websocket_server for Python benchmark dependencies
COPY orderbook/websocket_server/ ./websocket_server/
COPY benchmarks/run_benchmarks_docker.sh ./run_benchmarks.sh
COPY benchmarks/README.md ./
COPY benchmarks/SUMMARY.md ./

# Install Python dependencies
RUN pip3 install --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir -r python_benchmarks/requirements.txt && \
    pip3 install --no-cache-dir -r websocket_server/requirements.txt

# Create results directory
RUN mkdir -p /app/results /app/reports

# Make scripts executable
RUN chmod +x run_benchmarks.sh

# Set working directory
WORKDIR /app

# Default command: run all benchmarks
CMD ["./run_benchmarks.sh"]

