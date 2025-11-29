# Contributing to OrderBook

First off, thank you for considering contributing to OrderBook! It's people like you that make this project a great learning resource for the trading technology community.

## Code of Conduct

This project and everyone participating in it is governed by mutual respect and professionalism. Please be respectful and constructive in all interactions.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Describe the behavior you observed** and **what you expected**
- **Include logs, screenshots, or error messages**
- **Specify your environment** (OS, compiler version, Docker version)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **List any similar features** in other projects

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** if applicable
4. **Update documentation** to reflect your changes
5. **Ensure the build passes** (`cmake --build build`)
6. **Write a clear commit message**
7. **Submit a pull request**

## Development Setup

### C++ Backend

```bash
# Install dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y build-essential cmake g++ gdb

# Build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build

# Run tests
./build/ob_cli
```

### Python WebSocket Server

```bash
cd websocket_server
pip install -r requirements.txt
python server.py
```

### Docker Development

```bash
# Build and run
docker-compose up --build

# View logs
docker-compose logs -f

# Shell into container
docker exec -it orderbook-trading bash
```

## Coding Standards

### C++ Guidelines

- **C++20 Standard** - Use modern C++ features appropriately
- **SOLID Principles** - Maintain clean architecture
- **Const Correctness** - Use `const` wherever possible
- **Smart Pointers** - Prefer `unique_ptr`/`shared_ptr` over raw pointers
- **Naming Conventions**:
  - Classes: `PascalCase` (e.g., `OrderBook`)
  - Functions: `camelCase` (e.g., `addOrder`)
  - Variables: `snake_case` (e.g., `order_id`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_ORDERS`)
  - Interfaces: `I` prefix (e.g., `IOrderBook`)
- **Headers**: Use `#pragma once`
- **Includes**: Sort alphabetically, separate std/system/local
- **Comments**: Use `//` for single-line, document all public APIs

Example:
```cpp
#pragma once

#include <memory>
#include <string>

#include "orderbook/core/types.hpp"

namespace ob::book {

/// @brief Manages limit orders with price-time priority
class OrderBook final : public IOrderBook {
public:
    /// @brief Adds a new order to the book
    /// @param order The order to add
    /// @return true if successfully added
    bool addOrder(const Order& order) override;

private:
    std::map<Price, Level> m_bids;
    std::map<Price, Level> m_asks;
};

} // namespace ob::book
```

### Python Guidelines

- **PEP 8** - Follow Python style guide
- **Type Hints** - Use type annotations
- **Async/Await** - Proper async patterns for WebSocket
- **Error Handling** - Comprehensive try/except blocks
- **Logging** - Use Python `logging` module

Example:
```python
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

async def process_order(order: Dict[str, Any]) -> Optional[str]:
    """
    Process an incoming order.
    
    Args:
        order: Order dictionary with type, side, price, quantity
        
    Returns:
        Order ID if successful, None otherwise
    """
    try:
        # Implementation
        logger.info(f"Processing order: {order}")
        return order_id
    except Exception as e:
        logger.error(f"Failed to process order: {e}")
        return None
```

### JavaScript/HTML Guidelines

- **Modern ES6+** - Use arrow functions, const/let, async/await
- **Semantic HTML** - Proper HTML5 structure
- **Accessibility** - ARIA labels where needed
- **Responsive** - Mobile-friendly design

## Project Structure Guidelines

### Adding New Features

1. **C++ Components** go in appropriate namespace:
   - `ob::book` - OrderBook functionality
   - `ob::engine` - Matching engine
   - `ob::core` - Core types and utilities
   - `ob::oms` - Order management

2. **Headers** go in `include/orderbook/[namespace]/`
3. **Implementation** goes in `src/orderbook/[namespace]/`
4. **Tests** would go in `tests/` (future)

### Documentation

- Update relevant docs in `docs/` folder
- Add API documentation for new WebSocket messages
- Include examples for new features
- Update README.md if adding major features

## Performance Considerations

- **Profile before optimizing** - Use profilers (perf, valgrind)
- **Avoid unnecessary allocations** - Reuse objects where possible
- **Lock-free preferred** - But only where it makes sense
- **Benchmark changes** - Measure impact on latency

## Commit Messages

Use clear, descriptive commit messages:

```
feat: Add market order support to matching engine

- Implement immediate-or-cancel market orders
- Update WebSocket protocol to handle market orders
- Add tests for market order execution

Closes #123
```

Prefix types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `perf:` - Performance improvement
- `test:` - Adding tests
- `chore:` - Maintenance tasks

## Testing

Currently, testing is manual. When adding features:

1. **Test locally** with `ob_cli`
2. **Test with WebSocket** interface
3. **Test with Docker** build
4. **Document test scenarios** in PR description

## Questions?

Feel free to open an issue with the `question` label or start a discussion.

## Recognition

Contributors will be recognized in the project README and release notes.

Thank you for contributing! 🙏

