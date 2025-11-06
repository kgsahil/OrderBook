cmake_minimum_required(VERSION 3.20)

project(Orderbook CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(ORDERBOOK_ENABLE_SANITIZERS "Enable address/ub sanitizers" ON)
option(ORDERBOOK_VERBOSE_LOG "Enable verbose logging" ON)

include(GNUInstallDirs)

add_compile_options(-Wall -Wextra -Wpedantic -Wconversion -Wshadow)

if (ORDERBOOK_ENABLE_SANITIZERS)
  add_link_options(-fsanitize=address,undefined)
  add_compile_options(-fsanitize=address,undefined)
endif()

add_library(orderbook
  src/orderbook/book/order_book.cpp
  src/orderbook/engine/matching_engine.cpp
  src/orderbook/processors/order_processor.cpp
  src/orderbook/oms/order_management_system.cpp
)

target_include_directories(orderbook
  PUBLIC ${PROJECT_SOURCE_DIR}/include
)

target_compile_definitions(orderbook PRIVATE $<$<CONFIG:Release>:NDEBUG>)
if (ORDERBOOK_VERBOSE_LOG)
  target_compile_definitions(orderbook PUBLIC ORDERBOOK_VERBOSE_LOG=1)
endif()

add_executable(ob_cli apps/ob_cli.cpp)
target_link_libraries(ob_cli PRIVATE orderbook pthread)


