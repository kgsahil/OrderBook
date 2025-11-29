# Running Benchmarks in Docker

This guide explains how to run the OrderBook benchmarks in a Docker environment with all services running.

## Prerequisites

- Docker and Docker Compose installed
- All OrderBook services running (orderbook, dashboard, agents)

## Quick Start

### 1. Start All Services

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Run Benchmarks

```bash
# Run benchmarks with all services
docker-compose --profile benchmarks run --rm benchmarks

# Or use the helper script
./benchmarks/docker-run.sh
```

## Manual Execution

### Build Benchmark Image

```bash
docker-compose build benchmarks
```

### Run Specific Benchmark Types

```bash
# Run only C++ benchmarks
docker-compose run --rm benchmarks ./build/benchmarks

# Run only Python benchmarks
docker-compose run --rm benchmarks pytest python_benchmarks/ -v --benchmark-only

# Run with custom environment
docker-compose run --rm -e ORDERBOOK_HOST=localhost benchmarks
```

## Accessing Results

Results are saved to:
- `benchmarks/results/` - JSON, CSV, and text reports
- `benchmarks/reports/` - HTML reports (if generated)

Results are automatically mounted as volumes, so they persist on your host machine.

## Environment Variables

You can customize the benchmark execution with environment variables:

```bash
docker-compose run --rm \
  -e ORDERBOOK_HOST=orderbook \
  -e ORDERBOOK_PORT=8000 \
  -e TCP_HOST=orderbook \
  -e TCP_PORT=9999 \
  benchmarks
```

## Running End-to-End Benchmarks

For end-to-end benchmarks that require services:

```bash
# 1. Start services
docker-compose up -d

# 2. Wait for services to be healthy
docker-compose ps

# 3. Run benchmarks
docker-compose --profile benchmarks run --rm benchmarks

# 4. View results
cat benchmarks/results/cpp_benchmarks.txt
cat benchmarks/results/python_benchmarks.txt
```

## Troubleshooting

### Services Not Available

If benchmarks can't connect to services:

```bash
# Check service health
docker-compose ps

# Check service logs
docker-compose logs orderbook

# Verify network connectivity
docker-compose exec benchmarks curl http://orderbook:8000/health
```

### Build Failures

If C++ benchmarks fail to build:

```bash
# Rebuild with verbose output
docker-compose build --no-cache benchmarks

# Check build logs
docker-compose build benchmarks 2>&1 | tee build.log
```

### Python Benchmark Failures

If Python benchmarks fail:

```bash
# Check Python dependencies
docker-compose run --rm benchmarks pip list

# Run with verbose output
docker-compose run --rm benchmarks pytest python_benchmarks/ -vv
```

## Performance Considerations

When running benchmarks in Docker:

1. **CPU Limits**: Docker may limit CPU usage. For accurate results, run on dedicated hardware
2. **Network Latency**: Inter-container communication adds latency
3. **Resource Allocation**: Ensure sufficient CPU and memory allocated to containers

## Development Mode

For development and iteration:

```bash
# Mount source code for live editing
docker-compose run --rm \
  -v $(pwd)/benchmarks:/app \
  -v $(pwd)/orderbook:/app/orderbook:ro \
  benchmarks
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Benchmarks

on: [push, pull_request]

jobs:
  benchmarks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: docker-compose up -d
      - name: Run benchmarks
        run: docker-compose --profile benchmarks run --rm benchmarks
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: benchmarks/results/
```

