# -*- coding: utf-8 -*-
"""
健康检查路由

提供系统健康检查和状态监控端点
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

router = APIRouter()


class ComponentHealth(BaseModel):
    """组件健康状态"""
    name: str
    status: str  # healthy, degraded, unhealthy, unknown
    message: str
    response_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str  # healthy, degraded, unhealthy
    timestamp: str
    uptime_seconds: float
    version: str = "1.0.0"
    components: Dict[str, ComponentHealth]


class DetailedHealthResponse(BaseModel):
    """详细健康检查响应"""
    status: str
    timestamp: str
    uptime_seconds: float
    version: str
    environment: str
    components: Dict[str, ComponentHealth]
    metrics: Dict[str, Any]
    alerts: Dict[str, Any]


@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse)
@router.get("/basic", response_model=HealthResponse)
async def health_check():
    """基础健康检查"""
    return await check_health()


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """详细健康检查"""
    return await check_health_detailed()


@router.get("/ping")
async def ping():
    """Ping端点（用于负载均衡器健康检查）"""
    return {"status": "pong", "timestamp": datetime.now().isoformat()}


async def check_health() -> HealthResponse:
    """执行健康检查"""
    start_time = datetime.now()
    components = {}

    # 计算运行时间
    uptime = (start_time - datetime(2024, 1, 1)).total_seconds()

    # 检查PostgreSQL
    components["postgresql"] = await check_postgresql()

    # 检查Redis
    components["redis"] = await check_redis()

    # 检查RabbitMQ
    components["rabbitmq"] = await check_rabbitmq()

    # 检查TDengine（可选）
    components["tdengine"] = await check_tdengine()

    # 检查采集器
    components["collector"] = await check_collector()

    # 确定整体状态
    statuses = [c.status for c in components.values()]
    if "unhealthy" in statuses:
        overall_status = "unhealthy"
    elif "degraded" in statuses or "unknown" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now().isoformat(),
        uptime_seconds=uptime,
        version="1.0.0",
        components=components,
    )


async def check_health_detailed() -> DetailedHealthResponse:
    """执行详细健康检查"""
    basic_health = await check_health()

    # 获取额外的指标
    metrics = {}

    try:
        from ...performance.metrics import get_system_metrics_collector
        sys_collector = get_system_metrics_collector()
        metrics["system"] = sys_collector.collect_all()
    except Exception as e:
        metrics["system"] = {"error": str(e)}

    try:
        from ...performance.metrics import get_metrics_collector
        metrics_collector = get_metrics_collector()
        metrics["application"] = {
            "requests_total": metrics_collector.get_counter("requests.total"),
            "responses_5xx": metrics_collector.get_counter("responses.500"),
            "responses_4xx": metrics_collector.get_counter("responses.400"),
        }
    except Exception as e:
        metrics["application"] = {"error": str(e)}

    # 获取告警信息
    alerts = {}
    try:
        from ...alerts import get_alert_manager
        alert_manager = get_alert_manager()
        alerts = alert_manager.get_alert_stats()
    except Exception as e:
        alerts = {"error": str(e)}

    # 获取环境信息
    import os
    environment = os.getenv("ENVIRONMENT", "development")

    return DetailedHealthResponse(
        status=basic_health.status,
        timestamp=basic_health.timestamp,
        uptime_seconds=basic_health.uptime_seconds,
        version=basic_health.version,
        environment=environment,
        components=basic_health.components,
        metrics=metrics,
        alerts=alerts,
    )


async def check_postgresql() -> ComponentHealth:
    """检查PostgreSQL健康状态"""
    start = datetime.now()
    try:
        from ...db import get_postgres_client
        client = await get_postgres_client()
        is_healthy = await client.health_check()

        response_time = (datetime.now() - start).total_seconds() * 1000

        if is_healthy:
            return ComponentHealth(
                name="postgresql",
                status="healthy",
                message="OK",
                response_time_ms=response_time,
            )
        else:
            return ComponentHealth(
                name="postgresql",
                status="unhealthy",
                message="Health check failed",
                response_time_ms=response_time,
            )
    except Exception as e:
        return ComponentHealth(
            name="postgresql",
            status="unknown",
            message=str(e),
            response_time_ms=(datetime.now() - start).total_seconds() * 1000,
        )


async def check_redis() -> ComponentHealth:
    """检查Redis健康状态"""
    start = datetime.now()
    try:
        from ...cache import get_cache_manager
        cache = get_cache_manager()
        client = cache._get_client()

        await client.ping()
        response_time = (datetime.now() - start).total_seconds() * 1000

        # 获取Redis信息
        info = await client.info()

        return ComponentHealth(
            name="redis",
            status="healthy",
            message="OK",
            response_time_ms=response_time,
            metadata={"connected_clients": info.get("connected_clients")},
        )
    except Exception as e:
        return ComponentHealth(
            name="redis",
            status="unknown",
            message=str(e),
            response_time_ms=(datetime.now() - start).total_seconds() * 1000,
        )


async def check_rabbitmq() -> ComponentHealth:
    """检查RabbitMQ健康状态"""
    start = datetime.now()
    try:
        from ...messaging import get_rabbitmq_connection
        conn = await get_rabbitmq_connection()

        # 简单检查连接
        is_open = conn is not None and not conn.is_closed

        response_time = (datetime.now() - start).total_seconds() * 1000

        if is_open:
            return ComponentHealth(
                name="rabbitmq",
                status="healthy",
                message="OK",
                response_time_ms=response_time,
            )
        else:
            return ComponentHealth(
                name="rabbitmq",
                status="unhealthy",
                message="Connection not open",
                response_time_ms=response_time,
            )
    except Exception as e:
        return ComponentHealth(
            name="rabbitmq",
            status="unknown",
            message=str(e),
            response_time_ms=(datetime.now() - start).total_seconds() * 1000,
        )


async def check_tdengine() -> ComponentHealth:
    """检查TDengine健康状态"""
    start = datetime.now()
    try:
        from ...storage import _check_tdengine_available
        if not _check_tdengine_available():
            return ComponentHealth(
                name="tdengine",
                status="degraded",
                message="TDengine not available (optional)",
                response_time_ms=(datetime.now() - start).total_seconds() * 1000,
            )

        from ...api.app import get_td_client
        client = get_td_client()

        if not client:
            return ComponentHealth(
                name="tdengine",
                status="degraded",
                message="TDengine client not initialized",
                response_time_ms=(datetime.now() - start).total_seconds() * 1000,
            )

        is_healthy = await client.health_check()
        response_time = (datetime.now() - start).total_seconds() * 1000

        if is_healthy:
            return ComponentHealth(
                name="tdengine",
                status="healthy",
                message="OK",
                response_time_ms=response_time,
            )
        else:
            return ComponentHealth(
                name="tdengine",
                status="unhealthy",
                message="Health check failed",
                response_time_ms=response_time,
            )
    except Exception as e:
        return ComponentHealth(
            name="tdengine",
            status="unknown",
            message=str(e),
            response_time_ms=(datetime.now() - start).total_seconds() * 1000,
        )


async def check_collector() -> ComponentHealth:
    """检查数据采集器健康状态"""
    start = datetime.now()
    try:
        from ...api.app import get_scheduler
        scheduler = get_scheduler()

        if not scheduler:
            return ComponentHealth(
                name="collector",
                status="degraded",
                message="Scheduler not initialized",
                response_time_ms=(datetime.now() - start).total_seconds() * 1000,
            )

        stats = scheduler.get_stats()
        response_time = (datetime.now() - start).total_seconds() * 1000

        is_healthy = stats.get("is_running", False)

        return ComponentHealth(
            name="collector",
            status="healthy" if is_healthy else "degraded",
            message=f"Running: {is_healthy}, Tasks: {stats.get('total_tasks', 0)}",
            response_time_ms=response_time,
            metadata=stats,
        )
    except Exception as e:
        return ComponentHealth(
            name="collector",
            status="unknown",
            message=str(e),
            response_time_ms=(datetime.now() - start).total_seconds() * 1000,
        )
