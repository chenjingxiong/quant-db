# -*- coding: utf-8 -*-
"""
健康检查API 测试
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.api.routes import health
from backend.api.routes.health import (
    ComponentHealth,
    HealthResponse,
    DetailedHealthResponse,
)


# ===========================
# Health Response Models Tests
# ===========================

def test_component_health_model():
    """测试组件健康状态模型"""
    ch = ComponentHealth(
        name="test",
        status="healthy",
        message="OK",
        response_time_ms=5.5,
        metadata={"key": "value"}
    )

    assert ch.name == "test"
    assert ch.status == "healthy"
    assert ch.message == "OK"
    assert ch.response_time_ms == 5.5
    assert ch.metadata == {"key": "value"}


def test_health_response_model():
    """测试健康检查响应模型"""
    components = {
        "test": ComponentHealth(
            name="test",
            status="healthy",
            message="OK"
        )
    }

    response = HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=3600.0,
        version="1.0.0",
        components=components
    )

    assert response.status == "healthy"
    assert response.version == "1.0.0"
    assert "test" in response.components


def test_detailed_health_response_model():
    """测试详细健康检查响应模型"""
    components = {
        "test": ComponentHealth(
            name="test",
            status="healthy",
            message="OK"
        )
    }

    response = DetailedHealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=3600.0,
        version="1.0.0",
        environment="production",
        components=components,
        metrics={"test": "value"},
        alerts={"total": 0}
    )

    assert response.status == "healthy"
    assert response.environment == "production"
    assert response.metrics == {"test": "value"}
    assert response.alerts == {"total": 0}


# ===========================
# Health Check Functions Tests
# ===========================

@pytest.mark.asyncio
async def test_check_postgresql_healthy():
    """测试PostgreSQL健康检查（健康状态）"""
    mock_client = AsyncMock()
    mock_client.health_check = AsyncMock(return_value=True)

    with patch("backend.db.get_postgres_client", return_value=mock_client):
        result = await health.check_postgresql()

        assert result.status == "healthy"
        assert result.name == "postgresql"
        assert result.message == "OK"
        assert result.response_time_ms is not None


@pytest.mark.asyncio
async def test_check_postgresql_unhealthy():
    """测试PostgreSQL健康检查（不健康状态）"""
    mock_client = AsyncMock()
    mock_client.health_check = AsyncMock(return_value=False)

    with patch("backend.db.get_postgres_client", return_value=mock_client):
        result = await health.check_postgresql()

        assert result.status == "unhealthy"
        assert result.name == "postgresql"
        assert result.message == "Health check failed"


@pytest.mark.asyncio
async def test_check_postgresql_unknown():
    """测试PostgreSQL健康检查（未知状态）"""
    with patch("backend.db.get_postgres_client", side_effect=Exception("Connection error")):
        result = await health.check_postgresql()

        assert result.status == "unknown"
        assert result.name == "postgresql"
        assert "Connection error" in result.message


@pytest.mark.asyncio
async def test_check_redis_healthy():
    """测试Redis健康检查（健康状态）"""
    mock_redis_client = AsyncMock()
    mock_redis_client.ping = AsyncMock()
    mock_redis_client.info = AsyncMock(return_value={"connected_clients": 10})

    mock_cache = Mock()
    mock_cache._get_client = AsyncMock(return_value=mock_redis_client)

    with patch("backend.cache.get_cache_manager", return_value=mock_cache):
        result = await health.check_redis()

        assert result.status == "healthy"
        assert result.name == "redis"
        assert result.message == "OK"
        assert result.metadata.get("connected_clients") == 10


@pytest.mark.asyncio
async def test_check_redis_unknown():
    """测试Redis健康检查（未知状态）"""
    with patch("backend.cache.get_cache_manager", side_effect=Exception("Redis not available")):
        result = await health.check_redis()

        assert result.status == "unknown"
        assert result.name == "redis"


@pytest.mark.asyncio
async def test_check_rabbitmq_healthy():
    """测试RabbitMQ健康检查（健康状态）"""
    mock_conn = Mock()
    mock_conn.is_closed = False

    with patch("backend.messaging.get_rabbitmq_connection", return_value=mock_conn):
        result = await health.check_rabbitmq()

        assert result.status == "healthy"
        assert result.name == "rabbitmq"
        assert result.message == "OK"


@pytest.mark.asyncio
async def test_check_rabbitmq_unhealthy():
    """测试RabbitMQ健康检查（不健康状态）"""
    mock_conn = Mock()
    mock_conn.is_closed = True

    with patch("backend.messaging.get_rabbitmq_connection", return_value=mock_conn):
        result = await health.check_rabbitmq()

        assert result.status == "unhealthy"
        assert result.name == "rabbitmq"
        assert result.message == "Connection not open"


@pytest.mark.asyncio
async def test_check_tdengine_degraded():
    """测试TDengine健康检查（降级状态）"""
    with patch("backend.storage._check_tdengine_available", return_value=False):
        result = await health.check_tdengine()

        assert result.status == "degraded"
        assert result.name == "tdengine"


@pytest.mark.asyncio
async def test_check_collector_running():
    """测试采集器健康检查（运行中）"""
    mock_scheduler = Mock()
    mock_scheduler.get_stats = Mock(return_value={
        "is_running": True,
        "total_tasks": 5
    })

    with patch("backend.api.app.get_scheduler", return_value=mock_scheduler):
        result = await health.check_collector()

        assert result.status == "healthy"
        assert result.name == "collector"
        assert "Running: True" in result.message


@pytest.mark.asyncio
async def test_check_collector_degraded():
    """测试采集器健康检查（降级状态）"""
    mock_scheduler = Mock()
    mock_scheduler.get_stats = Mock(return_value={
        "is_running": False,
        "total_tasks": 5
    })

    with patch("backend.api.app.get_scheduler", return_value=mock_scheduler):
        result = await health.check_collector()

        assert result.status == "degraded"
        assert result.name == "collector"


# ===========================
# Overall Health Check Tests
# ===========================

@pytest.mark.asyncio
async def test_check_health_all_healthy():
    """测试整体健康检查（全部健康）"""
    with patch.object(health, "check_postgresql") as mock_pg, \
         patch.object(health, "check_redis") as mock_redis, \
         patch.object(health, "check_rabbitmq") as mock_mq, \
         patch.object(health, "check_tdengine") as mock_td, \
         patch.object(health, "check_collector") as mock_collector:

        mock_pg.return_value = ComponentHealth(
            name="postgresql", status="healthy", message="OK"
        )
        mock_redis.return_value = ComponentHealth(
            name="redis", status="healthy", message="OK"
        )
        mock_mq.return_value = ComponentHealth(
            name="rabbitmq", status="healthy", message="OK"
        )
        mock_td.return_value = ComponentHealth(
            name="tdengine", status="degraded", message="Not available"
        )
        mock_collector.return_value = ComponentHealth(
            name="collector", status="healthy", message="Running"
        )

        result = await health.check_health()

        assert result.status == "degraded"  # tdengine is degraded
        assert len(result.components) == 5


@pytest.mark.asyncio
async def test_check_health_unhealthy_component():
    """测试整体健康检查（有不健康组件）"""
    with patch.object(health, "check_postgresql") as mock_pg, \
         patch.object(health, "check_redis") as mock_redis, \
         patch.object(health, "check_rabbitmq") as mock_mq, \
         patch.object(health, "check_tdengine") as mock_td, \
         patch.object(health, "check_collector") as mock_collector:

        mock_pg.return_value = ComponentHealth(
            name="postgresql", status="unhealthy", message="Failed"
        )
        mock_redis.return_value = ComponentHealth(
            name="redis", status="healthy", message="OK"
        )
        mock_mq.return_value = ComponentHealth(
            name="rabbitmq", status="healthy", message="OK"
        )
        mock_td.return_value = ComponentHealth(
            name="tdengine", status="degraded", message="Not available"
        )
        mock_collector.return_value = ComponentHealth(
            name="collector", status="healthy", message="Running"
        )

        result = await health.check_health()

        assert result.status == "unhealthy"


@pytest.mark.asyncio
async def test_check_health_degraded_status():
    """测试整体健康检查（降级状态）"""
    with patch.object(health, "check_postgresql") as mock_pg, \
         patch.object(health, "check_redis") as mock_redis, \
         patch.object(health, "check_rabbitmq") as mock_mq, \
         patch.object(health, "check_tdengine") as mock_td, \
         patch.object(health, "check_collector") as mock_collector:

        mock_pg.return_value = ComponentHealth(
            name="postgresql", status="healthy", message="OK"
        )
        mock_redis.return_value = ComponentHealth(
            name="redis", status="healthy", message="OK"
        )
        mock_mq.return_value = ComponentHealth(
            name="rabbitmq", status="healthy", message="OK"
        )
        mock_td.return_value = ComponentHealth(
            name="tdengine", status="unknown", message="Error"
        )
        mock_collector.return_value = ComponentHealth(
            name="collector", status="healthy", message="Running"
        )

        result = await health.check_health()

        assert result.status == "degraded"


@pytest.mark.asyncio
async def test_check_health_detailed():
    """测试详细健康检查"""
    with patch.object(health, "check_health") as mock_check:
        mock_check.return_value = HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            uptime_seconds=3600.0,
            version="1.0.0",
            components={}
        )

        result = await health.check_health_detailed()

        assert result.status == "healthy"
        assert result.environment is not None


# ===========================
# API Endpoint Tests
# ===========================

@pytest.mark.asyncio
async def test_ping_endpoint():
    """测试ping端点"""
    result = await health.ping()

    assert result["status"] == "pong"
    assert "timestamp" in result
    assert isinstance(result["timestamp"], str)


# ===========================
# Status Determination Tests
# ===========================

def test_overall_status_healthy():
    """测试整体健康状态判定（健康）"""
    pass


def test_overall_status_unhealthy():
    """测试整体健康状态判定（不健康）"""
    pass


def test_overall_status_degraded():
    """测试整体健康状态判定（降级）"""
    pass


# ===========================
# Response Time Tests
# ===========================

@pytest.mark.asyncio
async def test_response_time_recorded():
    """测试响应时间被记录"""
    mock_client = AsyncMock()
    mock_client.health_check = AsyncMock(return_value=True)

    with patch("backend.db.get_postgres_client", return_value=mock_client):
        result = await health.check_postgresql()

        assert result.response_time_ms is not None
        assert result.response_time_ms >= 0


@pytest.mark.asyncio
async def test_response_time_accuracy():
    """测试响应时间的准确性"""
    import time

    async def slow_health_check():
        time.sleep(0.1)
        return True

    mock_client = AsyncMock()
    mock_client.health_check = slow_health_check

    with patch("backend.db.get_postgres_client", return_value=mock_client):
        result = await health.check_postgresql()

        assert result.response_time_ms >= 90


# ===========================
# Metadata Tests
# ===========================

@pytest.mark.asyncio
async def test_component_metadata():
    """测试组件元数据"""
    mock_redis_client = AsyncMock()
    mock_redis_client.ping = AsyncMock()
    mock_redis_client.info = AsyncMock(return_value={
        "connected_clients": 10,
        "used_memory": "256M",
        "total_keys": 1000
    })

    mock_cache = Mock()
    mock_cache._get_client = AsyncMock(return_value=mock_redis_client)

    with patch("backend.cache.get_cache_manager", return_value=mock_cache):
        result = await health.check_redis()

        assert result.metadata is not None
        assert "connected_clients" in result.metadata
