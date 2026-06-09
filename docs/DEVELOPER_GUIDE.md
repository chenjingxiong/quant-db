# Quant DB Developer Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Architecture Overview](#architecture-overview)
5. [Development Workflow](#development-workflow)
6. [Testing](#testing)
7. [Code Style](#code-style)
8. [Contributing](#contributing)

---

## Getting Started

### Prerequisites

- **Python:** 3.9 or higher
- **Docker:** 20.10 or higher
- **Docker Compose:** 2.0 or higher
- **PostgreSQL:** 14+ (optional, can use Docker)
- **Redis:** 6+ (optional, can use Docker)
- **RabbitMQ:** 3.9+ (optional, can use Docker)

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/quant-db.git
   cd quant-db
   ```

2. **Start services with Docker:**
   ```bash
   docker-compose up -d
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Run the API server:**
   ```bash
   python -m backend.main
   ```

5. **Access the API:**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Grafana: http://localhost:3000

---

## Development Environment Setup

### Using Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=quant_db
POSTGRES_USER=quant_user
POSTGRES_PASSWORD=quant_pass

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASS=guest

# TDengine (optional)
TDENGINE_AVAILABLE=false
TDENGINE_HOST=localhost
TDENGINE_PORT=6041
TDENGINE_USER=root
TDENGINE_PASS=taosdata
TDENGINE_DATABASE=quant_db

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Project Structure

```
quant-db/
├── backend/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── config/                 # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── api/                    # API layer
│   │   ├── __init__.py
│   │   ├── app.py              # FastAPI application
│   │   ├── models.py           # Pydantic models
│   │   ├── errors.py           # Error handlers
│   │   └── routes/             # API endpoints
│   │       ├── __init__.py
│   │       ├── stock.py
│   │       ├── futures.py
│   │       ├── index.py
│   │       ├── sector.py
│   │       ├── collect.py
│   │       ├── auth.py
│   │       ├── health.py
│   │       ├── alerts.py
│   │       └── websocket.py
│   ├── models/                 # Data models
│   │   ├── __init__.py
│   │   └── stock.py
│   ├── storage/                # Database storage
│   │   ├── __init__.py
│   │   ├── tdengine_client.py
│   │   └── schema_manager.py
│   ├── adapters/               # Data source adapters
│   │   ├── __init__.py
│   │   └── pytdx_adapter.py
│   ├── collectors/             # Data collectors
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── scheduler.py
│   ├── cache/                  # Cache layer
│   │   ├── __init__.py
│   │   ├── redis_client.py
│   │   ├── cache_manager.py
│   │   └── decorators.py
│   ├── db/                     # Database clients
│   │   ├── __init__.py
│   │   └── postgres_client.py
│   ├── messaging/              # Message queue
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── publisher.py
│   │   └── consumer.py
│   ├── middleware/             # Middleware
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── rate_limit.py
│   │   └── performance.py
│   ├── services/               # Business services
│   │   ├── __init__.py
│   │   └── auth/
│   ├── alerts/                 # Alerting system
│   │   ├── __init__.py
│   │   ├── alert_manager.py
│   │   ├── alert_rules.py
│   │   └── notifiers.py
│   └── performance/            # Performance monitoring
│       ├── __init__.py
│       ├── profiler.py
│       └── metrics.py
├── docker/                     # Docker configurations
│   ├── Dockerfile.backend
│   ├── postgres/
│   ├── redis/
│   ├── rabbitmq/
│   └── grafana/
├── scripts/                    # Utility scripts
│   ├── deploy.sh
│   └── backup.sh
├── tests/                      # Test files
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   ├── test_cache.py
│   ├── test_auth.py
│   └── test_integration.py
├── docs/                       # Documentation
│   ├── API.md
│   ├── DEVELOPER_GUIDE.md
│   └── ARCHITECTURE.md
├── plans/                      # Iteration plans
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .pre-commit-config.yaml
└── README.md
```

---

## Architecture Overview

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                            │
│  (FastAPI routes, WebSocket, Request validation)            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
│  (Business logic, Authentication, Authorization)            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                       Data Layer                             │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌─────────────┐  │
│  │ Postgres│  │  Redis  │  │RabbitMQ  │  │  TDengine   │  │
│  └─────────┘  └─────────┘  └──────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Adapter Layer                             │
│  (PytdxAdapter, external data sources)                      │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. API Layer
- **FastAPI Application:** Main web framework
- **Routes:** RESTful endpoints organized by domain
- **Models:** Pydantic models for request/response validation
- **Middleware:** Authentication, rate limiting, performance tracking

#### 2. Service Layer
- **Auth Service:** JWT and API key management
- **Cache Service:** Multi-strategy caching
- **Message Service:** Event publishing and consuming

#### 3. Data Layer
- **PostgreSQL:** User data, metadata, configuration
- **Redis:** Caching, rate limiting, session storage
- **RabbitMQ:** Message queue for async processing
- **TDengine:** Time-series data storage (optional)

#### 4. Adapter Layer
- **PytdxAdapter:** TongDaX data source connector
- **Extensible:** Support for additional data sources

---

## Development Workflow

### Git Workflow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

3. **Push and create PR:**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Convention

Follow Conventional Commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Maintenance tasks

Example:
```
feat(auth): add API key authentication

- Implement API key generation and validation
- Add endpoints for API key management
- Add rate limiting per API key
```

### Code Review Process

1. Ensure all tests pass
2. Run pre-commit hooks
3. Create pull request with description
4. Address review feedback
5. Get approval before merging

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=backend --cov-report=html

# Run integration tests
pytest tests/test_integration.py

# Run with verbose output
pytest -v
```

### Test Structure

```python
# tests/test_auth.py
import pytest
from backend.services.auth import get_password_handler

@pytest.fixture
async def password_handler():
    return get_password_handler()

@pytest.mark.asyncio
async def test_password_hash(password_handler):
    password = "SecurePass123!"
    hashed = await password_handler.hash(password)
    assert hashed != password
    assert await password_handler.verify(password, hashed)
```

### Writing Tests

1. **Unit Tests:** Test individual functions/classes
2. **Integration Tests:** Test component interactions
3. **API Tests:** Test HTTP endpoints
4. **Async Tests:** Use `@pytest.mark.asyncio`

### Test Coverage

Aim for:
- **Unit tests:** 80%+ coverage
- **Integration tests:** Critical paths covered
- **API tests:** All endpoints covered

---

## Code Style

### Python Style Guide

Follow PEP 8 with these modifications:

- **Line length:** 100 characters
- **Imports:** Group by standard library, third-party, local
- **Naming:**
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Type Hints

Use type hints for all function signatures:

```python
from typing import Optional, List

async def get_stock_quotes(
    symbols: List[str],
    limit: Optional[int] = None
) -> List[StockQuote]:
    """Fetch stock quotes for given symbols."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_sma(prices: List[float], period: int) -> float:
    """Calculate Simple Moving Average.

    Args:
        prices: List of price values.
        period: Number of periods for average.

    Returns:
        The SMA value.

    Raises:
        ValueError: If period is greater than prices length.
    """
    ...
```

### Error Handling

```python
# Use specific exceptions
try:
    result = await some_operation()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise APIException(
        status_code=503,
        detail="Service unavailable"
    )

# Always use async context managers
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

---

## Performance Considerations

### Database Queries

- Use connection pooling
- Implement query caching
- Batch operations when possible

### API Optimization

- Enable compression for large responses
- Use streaming for large datasets
- Implement pagination

### Caching Strategy

- Cache frequently accessed data
- Use appropriate TTL values
- Implement cache warming

---

## Debugging

### Logging

```python
from loguru import logger

logger.debug("Detailed debug info")
logger.info("General info")
logger.warning("Warning message")
logger.error("Error occurred")
```

### Profiling

```python
from backend.performance.profiler import profile_function

@profile_function(name="expensive_operation")
async def expensive_operation():
    ...
```

### Debug Mode

Enable debug mode in `.env`:

```bash
LOG_LEVEL=DEBUG
API_RELOAD=true
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Pull Request Guidelines

- Describe the changes clearly
- Reference related issues
- Include screenshots for UI changes
- Update documentation if needed

---

## Troubleshooting

### Common Issues

**Docker containers won't start:**
```bash
docker-compose down -v
docker-compose up -d
```

**Port already in use:**
```bash
# Change port in .env
API_PORT=8001
```

**Database connection error:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres
```

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/docs/)
- [Project API Docs](./API.md)
- [Architecture Docs](./ARCHITECTURE.md)
