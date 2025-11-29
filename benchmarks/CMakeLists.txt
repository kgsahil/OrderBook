cmake_minimum_required(VERSION 3.20)

project(OrderbookBenchmarks CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Configure Google Benchmark options before fetching
option(BENCHMARK_DOWNLOAD_DEPENDENCIES "Download dependencies for Google Benchmark" ON)
option(BENCHMARK_ENABLE_GTEST_TESTS "Enable Google Test for Google Benchmark" OFF)

# Find Google Benchmark
find_package(benchmark QUIET)
if(NOT benchmark_FOUND)
    message(STATUS "Google Benchmark not found. Fetching from GitHub...")
    include(FetchContent)
    FetchContent_Declare(
        googlebenchmark
        GIT_REPOSITORY https://github.com/google/benchmark.git
        GIT_TAG v1.8.3
    )
    FetchContent_MakeAvailable(googlebenchmark)
endif()

# Include orderbook headers and source
set(ORDERBOOK_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../orderbook")
include_directories(
    ${ORDERBOOK_ROOT}/include
)

# Build orderbook library for benchmarks
add_library(orderbook STATIC
    ${ORDERBOOK_ROOT}/src/orderbook/book/order_book.cpp
    ${ORDERBOOK_ROOT}/src/orderbook/engine/matching_engine.cpp
    ${ORDERBOOK_ROOT}/src/orderbook/processors/order_processor.cpp
    ${ORDERBOOK_ROOT}/src/orderbook/oms/order_management_system.cpp
    ${ORDERBOOK_ROOT}/src/orderbook/oms/instrument_manager.cpp
)

target_include_directories(orderbook PUBLIC ${ORDERBOOK_ROOT}/include)
target_compile_definitions(orderbook PRIVATE $<$<CONFIG:Release>:NDEBUG>)

# Benchmark executable
add_executable(benchmarks
    cpp/benchmark_orderbook.cpp
    cpp/benchmark_queue.cpp
    cpp/benchmark_matching.cpp
    cpp/benchmark_oms.cpp
    cpp/benchmark_load.cpp
)

target_link_libraries(benchmarks
    PRIVATE
    orderbook
    benchmark::benchmark
    pthread
)

# Compile options for benchmarks
target_compile_options(benchmarks PRIVATE
    -Wall -Wextra -Wpedantic
    -O3
    -march=native  # Optimize for current CPU
)

# Release build optimizations
target_compile_definitions(benchmarks PRIVATE
    $<$<CONFIG:Release>:NDEBUG>
)

# Output directory for results
set_target_properties(benchmarks PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/build"
)

