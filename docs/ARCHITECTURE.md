# Quant DB Architecture Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [Deployment Architecture](#deployment-architecture)
7. [Scalability Design](#scalability-design)
8. [Security Architecture](#security-architecture)
9. [Monitoring & Observability](#monitoring--observability)

---

## System Overview

Quant DB is a quantitative finance data platform designed for:
- **Real-time market data collection** from multiple sources
- **High-performance time-series data storage**
- **RESTful API** for data access
- **Real-time data streaming** via WebSocket
- **Comprehensive monitoring and alerting**

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                            Clients                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │
│  │  Web UI  │  │ Mobile   │  │ 3rd Party│  │   Monitoring     │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Load Balancer                                │
│                       (Nginx/Traefik)                               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       API Gateway Layer                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application (Multiple Instances)                     │  │
│  │  ├── Authentication (JWT/API Key)                            │  │
│  │  ├── Rate Limiting (Redis-based)                             │  │
│  │  ├── Request Validation                                      │  │
│  │  ├── Response Caching                                        │  │
│  │  └── WebSocket Support                                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Service Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Auth Service│  │Alert Manager │  │ Collector Scheduler      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Data Layer                                 │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ PostgreSQL │  │   Redis    │  │ RabbitMQ │  │  TDengine    │   │
│  │ (Metadata) │  │  (Cache)   │  │ (Events) │  │ (Time-Series)│   │
│  └────────────┘  └────────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        External Sources                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐      │
│  │ TongDaX API  │  │   Exchange   │  │  Data Providers      │      │
│  └──────────────┘  └──────────────┘  └──────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Principles

### 1. Separation of Concerns
- **API Layer:** Handles HTTP/WebSocket communication
- **Service Layer:** Business logic and orchestration
- **Data Layer:** Storage and retrieval operations
- **Adapter Layer:** External system integration

### 2. Async-First Design
- All I/O operations are asynchronous
- Non-blocking database queries
- Concurrent request handling

### 3. Scalability
- Horizontal scaling support
- Stateless API design
- Distributed caching
- Message queue for async processing

### 4. Resilience
- Circuit breakers for external calls
- Graceful degradation
- Automatic retries with backoff
- Health checks for all components

### 5. Observability
- Structured logging
- Performance metrics
- Distributed tracing (optional)
- Comprehensive alerting

---

## Component Architecture

### API Layer

#### FastAPI Application

**Purpose:** Web framework providing HTTP/WebSocket endpoints

**Key Features:**
- OpenAPI/Swagger auto-documentation
- Request validation with Pydantic
- Dependency injection system
- Background task support

**Routes Organization:**
```
/api/v1/
├── stocks/          # Stock data endpoints
├── futures/         # Futures data endpoints
├── indices/         # Index data endpoints
├── sectors/         # Sector data endpoints
├── collect/         # Collection management
├── auth/            # Authentication
└── alerts/          # Alert management
/health/             # Health check
/ws/                 # WebSocket endpoint
```

#### Middleware Stack

1. **CORS Middleware:** Cross-origin resource sharing
2. **Auth Middleware:** JWT/API key validation
3. **Rate Limit Middleware:** Request throttling
4. **Performance Middleware:** Request timing
5. **Error Handler:** Standardized error responses

### Service Layer

#### Authentication Service

```
┌─────────────────────────────────────┐
│        Authentication Flow          │
└─────────────────────────────────────┘

1. Register → Password Hash → Store User
2. Login → Validate → Generate JWT → Return Token
3. Request → Verify JWT → Attach User Context
4. API Key → Validate → Attach Permissions
```

**Components:**
- `PasswordHandler`: Hashing and verification
- `JWTHandler`: Token creation and validation
- `APIKeyHandler`: API key management
- `PermissionManager`: RBAC enforcement

#### Cache Service

**Strategies:**
- **Write-Through:** Write to cache and DB
- **Write-Behind:** Write to cache, async DB write
- **Cache-Aside:** Check cache, load if miss

**Configuration:**
```python
# Cache strategies per data type
CACHE_STRATEGIES = {
    "stock_quote": {
        "strategy": "write_behind",
        "ttl": 5,        # 5 seconds
        "max_size": 10000
    },
    "user_info": {
        "strategy": "write_through",
        "ttl": 3600,     # 1 hour
        "max_size": 1000
    }
}
```

#### Alert Service

```
┌─────────────────────────────────────────┐
│          Alert Flow                     │
└─────────────────────────────────────────┘

1. Monitor Loop (30s interval)
       │
2. Check Rules → Condition Met?
       │
3. Trigger Alert → Check Cooldown
       │
4. Send Notifications → Log Alert
       │
5. Monitor → Auto-Resolve (if condition clears)
```

**Components:**
- `AlertManager`: Rule evaluation and alert triggering
- `AlertRule`: Rule definition with condition checker
- `Notifier`: Multi-channel notification delivery
- `AlertHistory`: Historical alert tracking

### Data Layer

#### PostgreSQL

**Purpose:** Metadata storage

**Data Stored:**
- Users and authentication data
- API keys and permissions
- Collection task configurations
- Alert rules and history
- System metadata

**Schema:**
```sql
users                 -- User accounts
api_keys              -- API key management
roles                 -- Role definitions
permissions           -- Permission definitions
collection_tasks      -- Data collection configs
alert_rules           -- Alert rule definitions
alert_history         -- Alert event log
```

#### Redis

**Purpose:** Caching and session storage

**Data Structures:**
- **String:** Simple key-value (rate limit counters)
- **Hash:** Complex objects (stock quotes)
- **List:** Queues (pending operations)
- **Sorted Set:** Time-series caching (with timestamps)
- **Pub/Sub:** Real-time notifications

**Use Cases:**
```
┌────────────────────────────────────────┐
│           Redis Usage                  │
├────────────────────────────────────────┤
│ cache:stock:{symbol}     → Hash        │
│ rate_limit:{user}:{type} → String      │
│ session:{session_id}     → Hash        │
│ alerts:active            → List        │
│ metrics:requests         → Sorted Set  │
└────────────────────────────────────────┘
```

#### RabbitMQ

**Purpose:** Message queuing for async processing

**Exchanges:**
- `direct`: Point-to-point messaging
- `topic:** Topic-based routing
- `fanout`: Broadcast to all consumers

**Queues:**
```
┌────────────────────────────────────────┐
│         Queue Definitions              │
├────────────────────────────────────────┤
│ data.collection.requests               │
│ data.collection.responses              │
│ alerts.notifications                   │
│ system.metrics                         │
│ data.validation.requests               │
└────────────────────────────────────────┘
```

#### TDengine

**Purpose:** Time-series data storage

**Schema:**
```sql
-- Stable (Table Template)
CREATE STABLE stock_bars (
    ts TIMESTAMP,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    amount DOUBLE
) TAGS (symbol BINARY(20));

-- Create table for specific stock
CREATE TABLE stock_000001 USING stock_bars TAGS ('000001');
```

---

## Data Flow

### Real-time Data Collection

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Scheduler triggers collection task                          │
│                          │                                      │
│  2. Adapter fetches data from source (TongDaX)                 │
│                          │                                      │
│  3. Data validation and cleaning                               │
│                          │                                      │
│  4. Publish to RabbitMQ (topic: data.raw)                      │
│                          │                                      │
│  5. Consumer processes and stores to TDengine                   │
│                          │                                      │
│  6. Update Redis cache                                         │
│                          │                                      │
│  7. Notify WebSocket subscribers                               │
└─────────────────────────────────────────────────────────────────┘
```

### API Request Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Client Request                                                 │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐                                           │
│  │ Load Balancer   │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ API Gateway     │                                           │
│  │ - CORS          │                                           │
│  │ - Rate Limit    │                                           │
│  │ - Auth Check    │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ Route Handler   │                                           │
│  │ - Validation    │                                           │
│  │ - Business Logic│                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ Cache Check     │                                           │
│  │ (Redis)         │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│     ┌─────┴─────┐                                              │
│     │ Hit?      │                                              │
│     ├─────┬─────┤                                              │
│     │ No  │ Yes │                                              │
│     │     │     │                                              │
│     ▼     │     ▼                                              │
│  ┌────────┐  │  Return Cached                                 │
│  │ TDengine│  │  Data                                          │
│  │ Query  │  │                                                │
│  └───┬────┘  │                                                │
│      │      │                                                  │
│      ▼      │                                                  │
│  ┌────────┐  │                                                │
│  │Update  │  │                                                │
│  │ Cache  │──┘                                                │
│  └────────┘                                                   │
│      │                                                         │
│      ▼                                                         │
│  Return Response                                               │
└─────────────────────────────────────────────────────────────────┘
```

### WebSocket Data Push

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Client connects to /ws                                     │
│                    │                                            │
│  2. Connection stored with subscription list                   │
│                    │                                            │
│  3. New data arrives (from collector or cache update)          │
│                    │                                            │
│  4. Match subscribers to data symbols                          │
│                    │                                            │
│  5. Push data to matching clients                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Web Framework | FastAPI | 0.104+ | API server |
| ASGI Server | Uvicorn | 0.24+ | Async runtime |
| Database | PostgreSQL | 14+ | Metadata storage |
| Cache | Redis | 6+ | Caching layer |
| Message Queue | RabbitMQ | 3.9+ | Async messaging |
| Time-Series DB | TDengine | 3.0+ | Market data storage |
| ORM | asyncpg | 0.29+ | Async PostgreSQL |
| Validation | Pydantic | 2.0+ | Data validation |

### Supporting Technologies

| Purpose | Technology |
|---------|------------|
| Data Source | Pytdx (TongDax) |
| HTTP Client | httpx |
| Task Scheduling | APScheduler |
| Logging | loguru |
| Testing | pytest, pytest-asyncio |
| Code Quality | Black, isort, MyPy |
| Monitoring | Prometheus, Grafana |

---

## Deployment Architecture

### Docker Compose Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Host                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Nginx (Optional)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              FastAPI Backend (xN)                       │   │
│  │  ┌────────┐  ┌────────┐  ┌────────┐                    │   │
│  │  │ App 1  │  │ App 2  │  │ App 3  │  ...                │   │
│  │  └────────┘  └────────┘  └────────┘                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│  ┌──────────────┐  ┌──────────┐  ┌────────────┐               │
│  │  PostgreSQL  │  │  Redis   │  │  RabbitMQ  │               │
│  └──────────────┘  └──────────┘  └────────────┘               │
│                                                                 │
│  ┌──────────────┐  ┌──────────┐  ┌────────────┐               │
│  │   TDengine   │  │ Grafana  │  │ Prometheus │               │
│  └──────────────┘  └──────────┘  └────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### Production Deployment

```
┌────────────────────────────────────────────────────────────────────┐
│                         Kubernetes Cluster                        │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    Ingress Controller                      │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              │                                    │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                   FastAPI Deployment                       │   │
│  │  ┌──────────────────────────────────────────────────────┐  │   │
│  │  │               Pod (Multiple Replicas)                 │  │   │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐      │  │   │
│  │  │  │   FastAPI  │  │   FastAPI  │  │   FastAPI  │      │  │   │
│  │  │  │  Container │  │  Container │  │  Container │      │  │   │
│  │  │  └────────────┘  └────────────┘  └────────────┘      │  │   │
│  │  └──────────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────┘   │
│                              │                                    │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    StatefulSets                            │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐           │   │
│  │  │ PostgreSQL  │  │   Redis    │  │  RabbitMQ  │           │   │
│  │  │  (Primary)  │  │ (Cluster)  │  │  (Cluster) │           │   │
│  │  └────────────┘  └────────────┘  └────────────┘           │   │
│  └────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

---

## Scalability Design

### Horizontal Scaling

**API Servers:**
- Stateless design allows multiple instances
- Load balancer distributes requests
- Shared session storage (Redis)

**Database Scaling:**
- PostgreSQL: Read replicas for queries
- Redis: Cluster mode for horizontal scaling
- RabbitMQ: Cluster for high availability

### Performance Optimization

**Caching Strategy:**
```
L1 Cache: In-memory (process)
    │
L2 Cache: Redis (distributed)
    │
L3: Database (persistent)
```

**Connection Pooling:**
- PostgreSQL: asyncpg connection pool
- Redis: aioredis connection pool
- TDengine: Native connection pool

**Query Optimization:**
- Prepared statements
- Batch operations
- Query result pagination

---

## Security Architecture

### Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────────┐
│  Request → Auth Check → Permission Check → Resource Access     │
└─────────────────────────────────────────────────────────────────┘

Authentication Methods:
1. JWT Token (User session)
2. API Key (Programmatic access)
3. OAuth2 (Third-party integration)

Authorization:
- Role-Based Access Control (RBAC)
- Resource-level permissions
- API key scope restrictions
```

### Security Layers

1. **Network Security:**
   - TLS/SSL for all connections
   - Firewall rules
   - VPN for admin access

2. **Application Security:**
   - Input validation
   - SQL injection prevention
   - XSS protection
   - CSRF tokens

3. **Data Security:**
   - Encryption at rest (optional)
   - Secure password hashing
   - API key rotation
   - Audit logging

---

## Monitoring & Observability

### Metrics Collection

```
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Application Metrics                        │   │
│  │  - Request count/rate                                   │   │
│  │  - Response time (P50, P95, P99)                        │   │
│  │  - Error rate                                           │   │
│  │  - Active connections                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              System Metrics                             │   │
│  │  - CPU usage                                            │   │
│  │  - Memory usage                                         │   │
│  │  - Disk I/O                                             │   │
│  │  - Network I/O                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Business Metrics                           │   │
│  │  - Data collection status                               │   │
│  │  - Cache hit rate                                       │   │
│  │  - WebSocket connections                                │   │
│  │  - Active alerts                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Prometheus    │
                    │   + Grafana     │
                    └─────────────────┘
```

### Health Checks

**Levels:**
1. **Liveness:** Is the application running?
2. **Readiness:** Can the application handle requests?
3. **Deep Health:** Are all dependencies healthy?

**Components Checked:**
- PostgreSQL connectivity
- Redis connectivity
- RabbitMQ connectivity
- TDengine connectivity (optional)
- Collector scheduler status

### Alerting

**Predefined Alerts:**
| Condition | Severity | Action |
|-----------|----------|--------|
| CPU > 80% | WARNING | Notify |
| Memory > 1GB | WARNING | Notify |
| API Error Rate > 5% | ERROR | Notify + Auto-scale |
| DB Connection Lost | CRITICAL | Page + Auto-recovery |

---

## Future Enhancements

1. **Multi-Region Deployment**
2. **Event Sourcing for Audit Trail**
3. **GraphQL API Alternative**
4. **Machine Learning Integration**
5. **Advanced Analytics Pipeline**
