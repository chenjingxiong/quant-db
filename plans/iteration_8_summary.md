# 第8轮迭代：性能优化

## 迭代概览

本迭代专注于系统性能优化，包括性能分析工具、数据库连接池、缓存预热、性能监控中间件等。

---

## 完成内容

### 1. 性能分析模块 (`backend/performance/`)

#### Profiler (`profiler.py`)

**功能：**
- 函数级性能分析
- 上下文管理器支持
- 装饰器支持（同步/异步）
- 慢操作检测
- 性能统计报告

**使用示例：**
```python
from backend.performance import get_profiler

profiler = get_profiler()

# 方式1: 上下文管理器
with profiler.profile("database_query"):
    result = await db.execute(query)

# 方式2: 装饰器
@profile_function("expensive_operation")
async def my_function():
    ...

# 方式3: 手动记录
profiler.record("api_call", duration=0.5)

# 获取统计
stats = profiler.get_stats()
slow_ops = profiler.get_slow_queries(threshold=1.0)
profiler.print_summary()
```

#### MetricsCollector (`metrics.py`)

**功能：**
- 计数器（Counter）
- 仪表（Gauge）
- 时序指标（Series）
- 系统指标收集

**指标类型：**
```python
# 计数器
metrics.inc("api.requests", 1.0)
metrics.dec("api.requests", 1.0)

# 仪表
metrics.set("memory.usage", 1024)

# 时序指标
metrics.record("response.time", 0.5, tags={"endpoint": "/api/v1/stocks"})

# 耗时指标
metrics.timing("query.duration", 0.3)
```

**系统指标：**
- CPU使用率
- 内存使用情况
- IO统计
- 网络流量
- 磁盘使用

#### CacheWarmer (`cache_warmer.py`)

**功能：**
- 缓存预热任务注册
- 批量预热执行
- 自动刷新循环
- 热点数据预热

**预热任务：**
- 股票列表缓存
- 热门股票缓存
- 指数列表缓存
- 配置缓存

**使用示例：**
```python
from backend.performance import get_cache_warmer

warmer = get_cache_warmer()

# 手动预热
await warmer.warm_all()

# 启动自动刷新
async_warmer = AsyncCacheWarmer(refresh_interval=300)
await async_warmer.start_auto_refresh()
```

### 2. 数据库连接池 (`backend/db/pool.py`)

#### ConnectionPoolManager

**特性：**
- 异步连接池
- 连接复用
- 自动重连
- 事务支持
- 查询优化

**配置参数：**
```python
pool = ConnectionPoolManager(
    dsn="postgresql://...",
    min_size=5,      # 最小连接数
    max_size=20,     # 最大连接数
    max_queries=50000, # 单连接最大查询数
)
```

**使用方式：**
```python
# 方式1: 上下文管理器
async with pool.acquire() as conn:
    result = await conn.fetch("SELECT * FROM users")

# 方式2: 直接方法
rows = await pool.fetch("SELECT * FROM users WHERE id=$1", user_id)
row = await pool.fetchone("SELECT * FROM users WHERE id=$1", user_id)
value = await pool.fetchval("SELECT count(*) FROM users")

# 方式3: 事务
async with pool.transaction():
    await pool.execute("INSERT INTO users ...")
    await pool.execute("UPDATE users ...")
```

#### QueryOptimizer

**优化功能：**
- 分页查询优化
- 查询结果缓存
- 批量插入优化

```python
optimizer = QueryOptimizer(pool)

# 分页查询
result = await optimizer.fetch_paginated(
    "SELECT * FROM stocks WHERE symbol LIKE $1",
    page=1,
    page_size=20,
    "%600%"
)

# 缓存查询
rows = await optimizer.fetch_with_cache(
    "SELECT * FROM hot_stocks",
    cache_key="hot_stocks_list",
    cache_ttl=300
)

# 批量插入
count = await optimizer.batch_insert("stocks", data_list, batch_size=1000)
```

### 3. 性能监控中间件 (`backend/middleware/performance.py`)

#### PerformanceMiddleware

**功能：**
- 请求时间统计
- 慢请求检测
- 指标收集
- 性能响应头

**配置：**
```python
from backend.middleware.performance import PerformanceMiddleware

app.add_middleware(
    PerformanceMiddleware,
    enable_profiling=True,
    slow_request_threshold=1.0,  # 1秒
    enable_metrics=True,
)
```

**响应头：**
- `X-Request-ID`: 请求标识
- `X-Process-Time`: 处理时间（毫秒）

#### QueryPerformanceMiddleware

**功能：**
- SQL查询时间统计
- 慢查询检测
- 查询统计报告

#### CacheHitRateMiddleware

**功能：**
- 缓存命中率统计
- 命中/未命中/错误计数

```python
cache_middleware = get_cache_middleware()

# 记录缓存操作
cache_middleware.record_hit("stock_quotes")
cache_middleware.record_miss("stock_quotes")

# 获取统计
stats = cache_middleware.get_stats()
# {"hits": 100, "misses": 10, "errors": 0, "hit_rate": 0.909}
```

---

## 性能优化策略

### 1. 数据库优化

| 优化项 | 说明 | 效果 |
|--------|------|------|
| 连接池 | 复用连接，减少建立开销 | 50-70% |
| 批量操作 | 一次提交多条数据 | 80-90% |
| 查询缓存 | 缓存常用查询结果 | 90-99% |
| 分页优化 | 使用游标分页 | 30-50% |

### 2. 缓存优化

| 策略 | 说明 | TTL |
|------|------|-----|
| 热点数据 | 预热热门股票 | 1分钟 |
| 股票列表 | 缓存股票代码列表 | 1小时 |
| 配置数据 | 系统配置缓存 | 2小时 |
| 查询结果 | 复杂查询缓存 | 5分钟 |

### 3. API优化

| 优化项 | 说明 |
|--------|------|
| 异步处理 | 使用asyncio |
| 响应压缩 | gzip编码 |
| 数据分页 | 限制返回数据量 |
| 批量接口 | 减少请求次数 |

---

## 性能监控指标

### 关键指标（KPI）

| 指标 | 目标值 | 说明 |
|------|--------|------|
| API响应时间 | < 100ms (P95) | 大部分请求响应时间 |
| 数据库查询 | < 50ms (P95) | 查询执行时间 |
| 缓存命中率 | > 80% | 缓存有效性 |
| 错误率 | < 0.1% | 请求失败率 |
| 并发连接 | > 100 | 数据库连接数 |

### 监控仪表板

**实时监控：**
- 请求数 (QPS)
- 平均响应时间
- 错误率
- 缓存命中率
- 数据库连接池状态

**定期报告：**
- 慢请求列表
- 慢查询列表
- 性能趋势图
- 资源使用情况

---

## 使用指南

### 启用性能监控

**在FastAPI应用中：**
```python
from backend.middleware.performance import PerformanceMiddleware
from backend.middleware import get_cache_middleware

app.add_middleware(PerformanceMiddleware)
```

**性能分析：**
```python
from backend.performance import profile_function

@profile_function()
async def expensive_operation():
    ...
```

**查看统计：**
```python
from backend.performance import get_profiler, get_metrics_collector

profiler = get_profiler()
profiler.print_summary()

metrics = get_metrics_collector()
print(metrics.get_all_metrics())
```

---

## 项目文件更新

```
backend/
├── performance/
│   ├── __init__.py           # 性能模块入口 [NEW]
│   ├── profiler.py           # 性能分析器 [NEW]
│   ├── metrics.py            # 指标收集器 [NEW]
│   └── cache_warmer.py       # 缓存预热器 [NEW]
├── db/
│   └── pool.py               # 连接池管理 [NEW]
└── middleware/
    └── performance.py        # 性能中间件 [NEW]
```

---

## 下一步优化

1. **异步任务优化**
   - 后台任务队列
   - 定时任务优化

2. **内存优化**
   - 内存泄漏检测
   - 对象池化

3. **并发优化**
   - 协程池管理
   - 任务并发控制

---

*文档生成时间: 2026-03-20*
*迭代轮次: 8*
