#!/bin/bash

# OrderBook Benchmark Runner
# This script runs all benchmarks and generates reports

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 OrderBook Performance Benchmarks"
echo "===================================="
echo ""

# Create results directory
mkdir -p results
mkdir -p reports

# Build C++ benchmarks
echo "📦 Building C++ benchmarks..."
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --parallel
cd ..

# Run C++ benchmarks
echo ""
echo "⚡ Running C++ benchmarks..."
cd build
./benchmarks --benchmark_format=json > ../results/cpp_benchmarks.json
./benchmarks --benchmark_format=csv > ../results/cpp_benchmarks.csv
./benchmarks  # Human-readable output
cd ..

# Run Python benchmarks
echo ""
echo "🐍 Running Python benchmarks..."
cd python_benchmarks
python -m pytest . -v --benchmark-only --benchmark-json=../results/python_benchmarks.json
cd ..

# Generate summary
echo ""
echo "📊 Generating summary..."
python3 << 'EOF'
import json
import sys
from pathlib import Path

results_dir = Path("results")
summary = []

# Parse C++ results
cpp_file = results_dir / "cpp_benchmarks.json"
if cpp_file.exists():
    with open(cpp_file) as f:
        cpp_data = json.load(f)
        summary.append("\n=== C++ Benchmarks ===")
        for bench in cpp_data.get("benchmarks", []):
            name = bench.get("name", "")
            cpu_time = bench.get("cpu_time", 0)
            real_time = bench.get("real_time", 0)
            items_per_sec = bench.get("items_per_second", 0)
            summary.append(f"{name}:")
            summary.append(f"  CPU Time: {cpu_time:.2f} ns")
            summary.append(f"  Real Time: {real_time:.2f} ns")
            if items_per_sec > 0:
                summary.append(f"  Throughput: {items_per_sec:,.0f} ops/sec")

# Parse Python results
py_file = results_dir / "python_benchmarks.json"
if py_file.exists():
    with open(py_file) as f:
        py_data = json.load(f)
        summary.append("\n=== Python Benchmarks ===")
        for name, bench in py_data.items():
            stats = bench.get("stats", {})
            mean = stats.get("mean", 0)
            median = stats.get("median", 0)
            summary.append(f"{name}:")
            summary.append(f"  Mean: {mean*1e6:.2f} ms")
            summary.append(f"  Median: {median*1e6:.2f} ms")

print("\n".join(summary))
EOF

echo ""
echo "✅ Benchmarks complete! Results saved to results/ directory"
echo ""

