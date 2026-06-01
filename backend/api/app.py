# -*- coding: utf-8 -*-
"""
FastAPI 主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from starlette.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from loguru import logger
import time

from ..config import get_settings
from ..storage import TDEngineClient, SchemaManager, _check_tdengine_available
from ..adapters import PytdxAdapter
from ..collectors.scheduler import CollectorScheduler
from .routes import stock, futures, index, sector, collect, health, websocket, metrics as metrics_route, indicators, screener, portfolio, backtest, alerts
from .errors import (
    APIException,
    api_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)


# 全局实例
settings = get_settings()
td_client: TDEngineClient = None
collector_scheduler: CollectorScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global td_client, collector_scheduler

    logger.info("Starting Quant DB API...")

    # 记录应用启动时间
    from .routes.health import set_app_start_time
    set_app_start_time()

    # 初始化 TDengine 连接（如果可用）
    if _check_tdengine_available() and TDEngineClient is not None:
        try:
            td_client = TDEngineClient()
            await td_client.connect()

            # 初始化数据库结构
            schema_manager = SchemaManager(td_client)
            await schema_manager.init_database()
            await td_client.use_database(settings.tdengine_database)

            logger.info("TDengine database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize TDengine: {e}")
            td_client = None
    else:
        logger.warning("TDengine not available - running without TDengine support")

    # 初始化采集调度器
    try:
        collector_scheduler = CollectorScheduler()

        # 注册默认采集任务（可选）
        # 这里可以根据配置注册不同的采集任务

        await collector_scheduler.start()
        logger.info("Collector scheduler started")

    except Exception as e:
        logger.error(f"Failed to start collector scheduler: {e}")

    yield

    # 关闭时清理
    logger.info("Shutting down Quant DB API...")

    if collector_scheduler:
        await collector_scheduler.stop()

    if td_client:
        await td_client.disconnect()


def create_app() -> FastAPI:
    """创建FastAPI应用"""

    # OpenAPI文档配置
    openapi_tags = [
        {
            "name": "Root",
            "description": "根端点和基础信息"
        },
        {
            "name": "Health",
            "description": "系统健康检查和状态监控",
            "externalDocs": {
                "description": "健康检查文档",
                "url": "https://github.com/your-org/quant-db/docs/HEALTH.md"
            }
        },
        {
            "name": "Stocks",
            "description": "股票数据接口，包括实时行情、K线数据、股票列表等",
            "externalDocs": {
                "description": "股票数据文档",
                "url": "https://github.com/your-org/quant-db/docs/STOCKS.md"
            }
        },
        {
            "name": "Futures",
            "description": "期货数据接口"
        },
        {
            "name": "Indices",
            "description": "指数数据接口"
        },
        {
            "name": "Sectors",
            "description": "板块数据接口"
        },
        {
            "name": "Collection",
            "description": "数据采集任务管理和监控",
            "externalDocs": {
                "description": "采集管理文档",
                "url": "https://github.com/your-org/quant-db/docs/COLLECTION.md"
            }
        },
        {
            "name": "Authentication",
            "description": "用户认证和授权接口，包括注册、登录、API密钥管理",
            "externalDocs": {
                "description": "认证文档",
                "url": "https://github.com/your-org/quant-db/docs/AUTH.md"
            }
        },
        {
            "name": "WebSocket",
            "description": "实时数据推送接口"
        },
        {
            "name": "Alerts",
            "description": "告警管理和配置接口"
        },
        {
            "name": "Indicators",
            "description": "技术指标计算接口，支持SMA/EMA/MACD/KDJ/RSI/BOLL等"
        },
        {
            "name": "Screener",
            "description": "智能选股和自选股管理接口"
        }
    ]

    app = FastAPI(
        title="Quant DB API",
        description="""
# 量化金融数据采集与存储系统

Quant DB 是一个高性能的量化金融数据平台，提供实时行情数据获取、历史数据查询、数据采集管理等功能。

## 主要功能

### 数据获取
- **实时行情**: 获取股票、期货、指数的实时报价数据
- **K线数据**: 查询多个时间周期的历史K线数据
- **批量查询**: 支持批量获取多个证券的数据

### 数据采集
- **自动化采集**: 可配置的定时数据采集任务
- **多数据源**: 支持TongDaX等多种数据源
- **任务管理**: 启动、停止、监控采集任务

### 实时推送
- **WebSocket**: 实时推送行情数据更新
- **订阅模式**: 按需订阅关注的证券

### 系统监控
- **健康检查**: 多组件健康状态监控
- **告警系统**: 可配置的告警规则和多通道通知

## 认证方式

### JWT Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"username": "admin", "password": "password"}'
```

### API Key
```bash
curl "http://localhost:8000/api/v1/stocks/quotes?symbols=000001" \\
  -H "X-API-Key: your_api_key_here"
```

## 快速开始

```bash
# 启动服务
docker-compose up -d

# 访问文档
open http://localhost:8000/docs

# 获取股票行情
curl "http://localhost:8000/api/v1/stocks/quotes?symbols=000001,600000"
```

## 更多文档

- [API文档](https://github.com/your-org/quant-db/docs/API.md)
- [开发者指南](https://github.com/your-org/quant-db/docs/DEVELOPER_GUIDE.md)
- [架构文档](https://github.com/your-org/quant-db/docs/ARCHITECTURE.md)
""",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        openapi_tags=openapi_tags,
        contact={
            "name": "Quant DB Team",
            "email": "support@quantdb.example.com",
            "url": "https://github.com/your-org/quant-db"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "本地开发环境"
            },
            {
                "url": "https://api.quantdb.example.com",
                "description": "生产环境"
            },
            {
                "url": "https://staging-api.quantdb.example.com",
                "description": "预发布环境"
            }
        ]
    )

    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        path = request.url.path

        if path != "/health":
            logger.info(f"Request: {request.method} {path}")

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        if path != "/health":
            logger.info(
                f"Response: {request.method} {path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.2f}ms"
            )

        return response

    # 异常处理
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # 注册路由
    app.include_router(
        health.router,
        prefix="/health",
        tags=["Health"],
    )

    app.include_router(
        metrics_route.router,
        prefix="/metrics",
        tags=["Health"],
    )

    app.include_router(
        stock.router,
        prefix="/api/v1/stocks",
        tags=["Stocks"],
    )

    app.include_router(
        futures.router,
        prefix="/api/v1/futures",
        tags=["Futures"],
    )

    app.include_router(
        index.router,
        prefix="/api/v1/indices",
        tags=["Indices"],
    )

    app.include_router(
        sector.router,
        prefix="/api/v1/sectors",
        tags=["Sectors"],
    )

    app.include_router(
        collect.router,
        prefix="/api/v1/collect",
        tags=["Collection"],
    )

    # 认证路由
    from .routes import auth as auth_routes
    app.include_router(
        auth_routes.router,
        prefix="/api/v1",
        tags=["Authentication"],
    )

    # WebSocket路由
    app.include_router(
        websocket.router,
        tags=["WebSocket"],
    )

    # 技术指标路由
    app.include_router(
        indicators.router,
        prefix="/api/v1/indicators",
        tags=["Indicators"],
    )

    # 智能选股路由
    app.include_router(
        screener.router,
        prefix="/api/v1/screener",
        tags=["Screener"],
    )

    # 组合管理路由
    app.include_router(
        portfolio.router,
        prefix="/api/v1/portfolios",
        tags=["Portfolio"],
    )

    # 回测路由
    app.include_router(
        backtest.router,
        prefix="/api/v1/backtest",
        tags=["Backtest"],
    )

    # 告警路由
    app.include_router(
        alerts.router,
        prefix="/api/v1",
        tags=["Alerts"],
    )

    # 根路径
    @app.get(
        "/",
        tags=["Root"],
        summary="API基础信息",
        description="获取API的基础信息和可用端点",
        responses={
            200: {
                "description": "成功返回API信息",
                "content": {
                    "application/json": {
                        "example": {
                            "name": "Quant DB API",
                            "version": "1.0.0",
                            "status": "running",
                            "docs": "/docs",
                            "redoc": "/redoc",
                            "openapi": "/openapi.json",
                            "health": "/health",
                            "endpoints": {
                                "stocks": "/api/v1/stocks",
                                "futures": "/api/v1/futures",
                                "indices": "/api/v1/indices",
                                "sectors": "/api/v1/sectors",
                                "collection": "/api/v1/collect",
                                "auth": "/api/v1/auth",
                                "alerts": "/api/v1/alerts",
                                "websocket": "/ws"
                            }
                        }
                    }
                }
            }
        }
    )
    async def root():
        return {
            "name": "Quant DB API",
            "version": "1.0.0",
            "status": "running",
            "description": "量化金融数据采集与存储系统",
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "health": "/health",
            "endpoints": {
                "stocks": "/api/v1/stocks",
                "futures": "/api/v1/futures",
                "indices": "/api/v1/indices",
                "sectors": "/api/v1/sectors",
                "collection": "/api/v1/collect",
                "auth": "/api/v1/auth",
                "alerts": "/api/v1/alerts",
                "indicators": "/api/v1/indicators",
                "websocket": "/ws"
            }
        }

    return app


# 创建应用实例
app = create_app()


def get_td_client() -> TDEngineClient:
    """获取TDengine客户端"""
    return td_client


def get_scheduler() -> CollectorScheduler:
    """获取采集调度器"""
    return collector_scheduler
