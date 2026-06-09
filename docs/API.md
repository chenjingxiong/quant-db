# Quant DB API Documentation

## Overview

Quant DB API is a quantitative finance data collection and storage system built with FastAPI. It provides RESTful endpoints for accessing real-time and historical market data, managing data collection tasks, and system monitoring.

**Base URL:** `http://localhost:8000`

**API Version:** v1

## Authentication

### JWT Token Authentication

Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```http
Authorization: Bearer <access_token>
```

### API Key Authentication

Alternatively, you can use API keys:

```http
Authorization: Bearer <api_key>
X-API-Key: <api_key>
```

### Getting Tokens

1. **Register a new user:**
   ```bash
   POST /api/v1/auth/register
   ```

2. **Login to get tokens:**
   ```bash
   POST /api/v1/auth/login
   ```

3. **Refresh access token:**
   ```bash
   POST /api/v1/auth/refresh
   ```

---

## API Endpoints

### Health Check

#### Check System Health

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-20T10:00:00",
  "uptime_seconds": 1234567,
  "version": "1.0.0",
  "components": {
    "postgresql": {
      "name": "postgresql",
      "status": "healthy",
      "message": "OK",
      "response_time_ms": 5.2
    },
    "redis": {
      "name": "redis",
      "status": "healthy",
      "message": "OK",
      "response_time_ms": 1.1
    },
    "rabbitmq": {
      "name": "rabbitmq",
      "status": "healthy",
      "message": "OK",
      "response_time_ms": 3.4
    },
    "tdengine": {
      "name": "tdengine",
      "status": "degraded",
      "message": "TDengine not available (optional)",
      "response_time_ms": 0
    },
    "collector": {
      "name": "collector",
      "status": "healthy",
      "message": "Running: true, Tasks: 5",
      "response_time_ms": 0.5
    }
  }
}
```

#### Detailed Health Check

```http
GET /health/detailed
```

**Authentication:** Required

Returns detailed system metrics and alert statistics.

---

### Stocks

#### Get Real-time Quotes

```http
GET /api/v1/stocks/quotes?symbols=000001,600000
```

**Parameters:**
- `symbols` (required): Comma-separated stock symbols

**Response:**
```json
[
  {
    "symbol": "000001",
    "ts": "2024-03-20T10:00:00",
    "open": 10.50,
    "high": 10.80,
    "low": 10.45,
    "close": 10.75,
    "pre_close": 10.60,
    "volume": 12345678.0,
    "amount": 134567890.0,
    "change": 0.15,
    "change_percent": 1.42
  }
]
```

#### Get K-line Data

```http
GET /api/v1/stocks/bars?symbol=000001&interval=1day&limit=100
```

**Parameters:**
- `symbol` (required): Stock code
- `interval`: K-line period (1min, 5min, 15min, 30min, 60min, 1day, 1week, 1month)
- `start_time`: Start time (ISO 8601)
- `end_time`: End time (ISO 8601)
- `limit`: Number of records (1-10000, default: 100)

**Response:**
```json
[
  {
    "symbol": "000001",
    "interval": "1day",
    "ts": "2024-03-20T00:00:00",
    "open": 10.50,
    "high": 10.80,
    "low": 10.45,
    "close": 10.75,
    "volume": 12345678.0,
    "amount": 134567890.0
  }
]
```

#### Get Stock List

```http
GET /api/v1/stocks/list?market=SH&limit=5000
```

**Parameters:**
- `market`: Market filter (SH/SZ)
- `limit`: Number limit (1-50000, default: 5000)

**Response:**
```json
{
  "symbols": [
    {
      "symbol": "600000",
      "name": "浦发银行",
      "market": "SH"
    }
  ],
  "total": 1
}
```

#### Get Single Stock Quote

```http
GET /api/v1/stocks/{symbol}/quote
```

#### Get Stock Detail

```http
GET /api/v1/stocks/{symbol}/detail
```

---

### Futures

#### Get Futures Quotes

```http
GET /api/v1/futures/quotes?symbols=IF2403,IH2403
```

#### Get Futures K-line Data

```http
GET /api/v1/futures/bars?symbol=IF2403&interval=1day&limit=100
```

#### Get Futures List

```http
GET /api/v1/futures/list?exchange=CFFEX
```

---

### Indices

#### Get Index Quotes

```http
GET /api/v1/indices/quotes?symbols=000001,399001
```

#### Get Index K-line Data

```http
GET /api/v1/indices/bars?symbol=000001&interval=1day&limit=100
```

#### Get Index List

```http
GET /api/v1/indices/list
```

---

### Sectors

#### Get Sector List

```http
GET /api/v1/sectors/list
```

#### Get Sector Stocks

```http
GET /api/v1/sectors/{sector_id}/stocks
```

---

### Data Collection

#### Get Collection Tasks

```http
GET /api/v1/collect/tasks
```

**Authentication:** Required

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "stock_quotes",
      "name": "Stock Quotes Collector",
      "status": "running",
      "enabled": true,
      "last_run": "2024-03-20T10:00:00",
      "next_run": "2024-03-20T10:05:00",
      "total_runs": 1000,
      "success_count": 995,
      "failed_count": 5
    }
  ]
}
```

#### Start Collection Task

```http
POST /api/v1/collect/tasks/{task_id}/start
```

**Authentication:** Required

#### Stop Collection Task

```http
POST /api/v1/collect/tasks/{task_id}/stop
```

**Authentication:** Required

#### Get Collection Stats

```http
GET /api/v1/collect/stats
```

**Authentication:** Required

---

### Authentication

#### Register User

```http
POST /api/v1/auth/register
```

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "role": "user"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "username": "johndoe",
  "email": "john@example.com",
  "role": "user"
}
```

#### Login

```http
POST /api/v1/auth/login
```

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "sub": "1",
    "username": "johndoe",
    "email": "john@example.com",
    "role": "admin"
  }
}
```

#### Get Current User

```http
GET /api/v1/auth/me
```

**Authentication:** Required

#### Create API Key

```http
POST /api/v1/auth/apikey
```

**Authentication:** Required

**Request Body:**
```json
{
  "name": "Production Key",
  "scopes": ["read", "write"]
}
```

**Response:**
```json
{
  "api_key": "qdb_sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "key_id": "qdb_1_1710929600",
  "name": "Production Key",
  "scopes": ["read", "write"],
  "created_at": "2024-03-20T10:00:00"
}
```

#### List API Keys

```http
GET /api/v1/auth/apikey
```

**Authentication:** Required

#### Delete API Key

```http
DELETE /api/v1/auth/apikey/{key_id}
```

**Authentication:** Required

#### Change Password

```http
POST /api/v1/auth/password/change
```

**Authentication:** Required

#### Reset Password

```http
POST /api/v1/auth/password/reset
```

---

### Alerts

#### Get Alerts

```http
GET /api/v1/alerts?status=active&severity=error
```

**Authentication:** Required

**Parameters:**
- `status`: Filter by status (active/resolved/acknowledged/silenced)
- `severity`: Filter by severity (info/warning/error/critical)

**Response:**
```json
{
  "total": 5,
  "active": 3,
  "alerts": [
    {
      "id": "high_cpu_usage_1710929600",
      "rule_id": "high_cpu_usage",
      "title": "高CPU使用率",
      "message": "CPU使用率超过80%",
      "severity": "warning",
      "status": "active",
      "created_at": "2024-03-20T10:00:00",
      "metadata": {
        "cpu_percent": 85.5
      }
    }
  ]
}
```

#### Get Alert Statistics

```http
GET /api/v1/alerts/stats
```

**Authentication:** Required

**Response:**
```json
{
  "total_alerts": 100,
  "active_alerts": 5,
  "resolved_alerts": 95,
  "by_severity": {
    "info": 20,
    "warning": 50,
    "error": 25,
    "critical": 5
  },
  "total_rules": 8,
  "enabled_rules": 8
}
```

#### Execute Alert Action

```http
POST /api/v1/alerts/{alert_id}/action
```

**Authentication:** Required

**Request Body:**
```json
{
  "action": "acknowledge"
}
```

**Actions:**
- `acknowledge`: Acknowledge the alert
- `resolve`: Mark as resolved
- `silence`: Disable the alert rule

#### Get Alert Rules

```http
GET /api/v1/alerts/rules
```

**Authentication:** Required

#### Enable/Disable Rule

```http
POST /api/v1/alerts/rules/{rule_id}/enable
POST /api/v1/alerts/rules/{rule_id}/disable
```

**Authentication:** Required (Admin)

---

### WebSocket

#### Connect to Real-time Data Stream

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// Subscribe to symbols
ws.send(JSON.stringify({
  action: 'subscribe',
  symbols: ['000001', '600000']
}));

// Handle messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

// Unsubscribe
ws.send(JSON.stringify({
  action: 'unsubscribe',
  symbols: ['000001']
}));
```

**Message Types:**
- `quote`: Real-time quote updates
- `bar`: K-line data updates
- `error`: Error messages

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Rate Limiting

API requests are rate limited based on the endpoint:

- Authentication endpoints: 3-10 requests/hour
- Data endpoints: 100-1000 requests/minute
- Admin endpoints: 10 requests/minute

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1710929660
```

---

## Data Models

### Stock Quote

| Field | Type | Description |
|-------|------|-------------|
| symbol | string | Stock code |
| ts | string | Timestamp (ISO 8601) |
| open | float | Opening price |
| high | float | Highest price |
| low | float | Lowest price |
| close | float | Closing price |
| pre_close | float | Previous close |
| volume | float | Trading volume |
| amount | float | Trading amount |
| change | float | Price change |
| change_percent | float | Change percentage |

### K-line Bar

| Field | Type | Description |
|-------|------|-------------|
| symbol | string | Stock code |
| interval | string | Time interval |
| ts | string | Timestamp |
| open | float | Open price |
| high | float | High price |
| low | float | Low price |
| close | float | Close price |
| volume | float | Volume |
| amount | float | Amount |

---

## Interactive Documentation

The API includes interactive documentation powered by Swagger UI and ReDoc:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## SDK Examples

### Python

```python
import httpx

async def get_stock_quote(symbol: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v1/stocks/quotes",
            params={"symbols": symbol}
        )
        return response.json()
```

### JavaScript/TypeScript

```typescript
async function getStockQuote(symbol: string) {
  const response = await fetch(
    `http://localhost:8000/api/v1/stocks/quotes?symbols=${symbol}`
  );
  return await response.json();
}
```

### cURL

```bash
curl "http://localhost:8000/api/v1/stocks/quotes?symbols=000001"
```

---

## Changelog

### Version 1.0.0 (2024-03-20)
- Initial release
- Stock, Futures, Index data endpoints
- Authentication and authorization
- Real-time WebSocket streaming
- Monitoring and alerting
