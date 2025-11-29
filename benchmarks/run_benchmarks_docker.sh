#!/bin/bash

# Benchmark runner for Docker environment
# This version is optimized for running inside Docker with services available

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 OrderBook Performance Benchmarks (Docker)"
echo "============================================="
echo ""

# Wait for services to be ready
echo "⏳ Waiting for OrderBook service..."
ORDERBOOK_HOST=${ORDERBOOK_HOST:-orderbook}
ORDERBOOK_PORT=${ORDERBOOK_PORT:-8000}
TCP_PORT=${TCP_PORT:-9999}

for i in {1..30}; do
    if curl -s "http://${ORDERBOOK_HOST}:${ORDERBOOK_PORT}/health" > /dev/null 2>&1; then
        echo "✅ OrderBook service is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ OrderBook service not available after 30 attempts"
        exit 1
    fi
    sleep 2
done

# Create results directory
mkdir -p results
mkdir -p reports

# Run C++ benchmarks (already built in Docker image)
echo ""
echo "⚡ Running C++ benchmarks..."
# Run human-readable first to avoid JSON parsing issues
./benchmarks 2>&1 | tee results/cpp_benchmarks.txt
# Then try JSON/CSV (may fail due to memory issues, but that's okay)
./benchmarks --benchmark_format=json > results/cpp_benchmarks.json 2>&1 || echo "JSON output failed (non-critical)"
./benchmarks --benchmark_format=csv > results/cpp_benchmarks.csv 2>&1 || echo "CSV output failed (non-critical)"

# Run Python benchmarks (with service connection)
echo ""
echo "🐍 Running Python benchmarks..."
cd python_benchmarks

# Set environment variables for service connection
export ORDERBOOK_HOST=${ORDERBOOK_HOST}
export ORDERBOOK_PORT=${ORDERBOOK_PORT}
export TCP_HOST=${ORDERBOOK_HOST}
export TCP_PORT=${TCP_PORT}

# Add websocket_server to Python path
export PYTHONPATH=/app/websocket_server:$PYTHONPATH

# Run benchmarks - use explicit test file discovery
pytest benchmark_tcp_client.py benchmark_websocket.py -v --benchmark-only \
    --benchmark-json=../results/python_benchmarks.json \
    2>&1 | tee ../results/python_benchmarks.txt || true

cd ..

# Generate summary
echo ""
echo "📊 Generating summary..."
python3 << 'EOF'
import json
import sys
from pathlib import Path

results_dir = Path("results")
summary = ["\n=== Benchmark Results Summary ===\n"]

# Parse C++ results
cpp_file = results_dir / "cpp_benchmarks.json"
if cpp_file.exists():
    try:
        with open(cpp_file) as f:
            cpp_data = json.load(f)
            summary.append("=== C++ Benchmarks ===")
            for bench in cpp_data.get("benchmarks", []):
                name = bench.get("name", "")
                cpu_time = bench.get("cpu_time", 0)
                real_time = bench.get("real_time", 0)
                items_per_sec = bench.get("items_per_second", 0)
                summary.append(f"\n{name}:")
                summary.append(f"  CPU Time: {cpu_time:.2f} ns")
                summary.append(f"  Real Time: {real_time:.2f} ns")
                if items_per_sec > 0:
                    summary.append(f"  Throughput: {items_per_sec:,.0f} ops/sec")
    except Exception as e:
        summary.append(f"Error parsing C++ results: {e}")

# Parse Python results
py_file = results_dir / "python_benchmarks.json"
if py_file.exists():
    try:
        with open(py_file) as f:
            py_data = json.load(f)
            summary.append("\n=== Python Benchmarks ===")
            for name, bench in py_data.items():
                stats = bench.get("stats", {})
                mean = stats.get("mean", 0)
                median = stats.get("median", 0)
                summary.append(f"\n{name}:")
                summary.append(f"  Mean: {mean*1e6:.2f} ms")
                summary.append(f"  Median: {median*1e6:.2f} ms")
    except Exception as e:
        summary.append(f"Error parsing Python results: {e}")

print("\n".join(summary))
EOF

echo ""
echo "✅ Benchmarks complete! Results saved to results/ directory"
echo ""

