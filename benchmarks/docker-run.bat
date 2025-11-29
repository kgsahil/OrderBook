@echo off
REM Docker-based benchmark runner for Windows
REM This script runs benchmarks against the running OrderBook services

setlocal enabledelayedexpansion

echo 🚀 OrderBook Docker Benchmarks
echo ===============================
echo.

REM Check if services are running
echo 📡 Checking services...
docker-compose ps | findstr /C:"orderbook-service" | findstr /C:"Up" >nul
if errorlevel 1 (
    echo ❌ OrderBook service is not running!
    echo    Please start services first: docker-compose up -d
    exit /b 1
)

echo ✅ Services are running
echo.

REM Build benchmark image if not exists
echo 🔨 Building benchmark image...
docker-compose build benchmarks
if errorlevel 1 (
    echo ❌ Failed to build benchmark image
    exit /b 1
)

REM Run benchmarks
echo.
echo ⚡ Running benchmarks...
docker-compose --profile benchmarks run --rm benchmarks
if errorlevel 1 (
    echo ❌ Benchmarks failed
    exit /b 1
)

echo.
echo ✅ Benchmarks complete! Results saved to benchmarks/results/

