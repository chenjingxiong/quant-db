# -*- coding: utf-8 -*-
"""
WebSocket API 测试
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.api.websocket import ConnectionManager, manager


# ===========================
# ConnectionManager Tests
# ===========================

@pytest.mark.asyncio
async def test_connection_manager_initialization():
    """测试连接管理器初始化"""
    mgr = ConnectionManager()

    assert mgr is not None
    assert len(mgr.active_connections) == 0
    assert len(mgr.subscriptions) == 0


@pytest.mark.asyncio
async def test_connect():
    """测试WebSocket连接"""
    mgr = ConnectionManager()

    websocket = AsyncMock()

    await mgr.connect(websocket, "test_client_1")

    assert "test_client_1" in mgr.active_connections
    assert "test_client_1" in mgr.connection_subscriptions


@pytest.mark.asyncio
async def test_disconnect():
    """测试WebSocket断开连接"""
    mgr = ConnectionManager()

    websocket = AsyncMock()

    await mgr.connect(websocket, "test_client_1")
    mgr.disconnect("test_client_1")

    assert "test_client_1" not in mgr.active_connections
    assert "test_client_1" not in mgr.connection_subscriptions


@pytest.mark.asyncio
async def test_subscribe():
    """测试订阅"""
    mgr = ConnectionManager()

    websocket = AsyncMock()

    await mgr.connect(websocket, "test_client_1")
    await mgr.subscribe("test_client_1", "stock:quotes:000001")
    await mgr.subscribe("test_client_1", "stock:quotes:600000")

    assert "stock:quotes:000001" in mgr.connection_subscriptions["test_client_1"]
    assert "stock:quotes:600000" in mgr.connection_subscriptions["test_client_1"]
    assert "test_client_1" in mgr.subscriptions.get("stock:quotes:000001", set())


@pytest.mark.asyncio
async def test_unsubscribe():
    """测试取消订阅"""
    mgr = ConnectionManager()

    websocket = AsyncMock()

    await mgr.connect(websocket, "test_client_1")
    await mgr.subscribe("test_client_1", "stock:quotes:000001")
    await mgr.subscribe("test_client_1", "stock:quotes:600000")
    await mgr.unsubscribe("test_client_1", "stock:quotes:000001")

    assert "stock:quotes:000001" not in mgr.connection_subscriptions["test_client_1"]
    assert "stock:quotes:600000" in mgr.connection_subscriptions["test_client_1"]


@pytest.mark.asyncio
async def test_send_personal_message():
    """测试发送个人消息"""
    mgr = ConnectionManager()

    websocket = AsyncMock()

    await mgr.connect(websocket, "test_client_1")

    message = {"type": "test", "data": "hello"}
    result = await mgr.send_personal_message(message, "test_client_1")

    assert result is True
    assert websocket.send_json.called


@pytest.mark.asyncio
async def test_broadcast():
    """测试广播消息"""
    mgr = ConnectionManager()

    websocket1 = AsyncMock()
    websocket2 = AsyncMock()

    await mgr.connect(websocket1, "client_1")
    await mgr.connect(websocket2, "client_2")

    # 两个客户端都订阅同一主题
    await mgr.subscribe("client_1", "stock:quotes")
    await mgr.subscribe("client_2", "stock:quotes")

    message = {"type": "broadcast", "data": "hello all"}
    await mgr.broadcast(message, "stock:quotes")

    assert websocket1.send_json.called
    assert websocket2.send_json.called


@pytest.mark.asyncio
async def test_broadcast_to_topic_subscribers():
    """测试广播给订阅了特定主题的客户端"""
    mgr = ConnectionManager()

    websocket1 = AsyncMock()
    websocket2 = AsyncMock()

    await mgr.connect(websocket1, "client_1")
    await mgr.connect(websocket2, "client_2")

    await mgr.subscribe("client_1", "stock:quotes:000001")
    await mgr.subscribe("client_2", "stock:quotes:600000")

    message = {
        "type": "quote",
        "symbol": "000001",
        "data": {"price": 10.50}
    }

    await mgr.broadcast(message, "stock:quotes:000001")

    assert websocket1.send_json.called
    assert not websocket2.send_json.called


@pytest.mark.asyncio
async def test_get_connection_count():
    """测试获取连接数"""
    mgr = ConnectionManager()
    assert mgr.get_connection_count() == 0

    websocket1 = AsyncMock()
    websocket2 = AsyncMock()

    await mgr.connect(websocket1, "client_1")
    await mgr.connect(websocket2, "client_2")

    assert mgr.get_connection_count() == 2


@pytest.mark.asyncio
async def test_get_stats():
    """测试获取统计信息"""
    mgr = ConnectionManager()

    websocket = AsyncMock()
    await mgr.connect(websocket, "test_client")
    await mgr.subscribe("test_client", "stock:quotes:000001")

    stats = mgr.get_stats()

    assert "total_connections" in stats
    assert stats["total_connections"] == 1


def test_get_connection_manager():
    """测试获取全局连接管理器实例"""
    assert manager is not None
    assert isinstance(manager, ConnectionManager)


# ===========================
# WebSocket Endpoint Tests
# ===========================

@pytest.mark.asyncio
async def test_websocket_endpoint_connect():
    """测试WebSocket端点连接"""
    pass


@pytest.mark.asyncio
async def test_websocket_subscribe_message():
    """测试WebSocket订阅消息处理"""
    mgr = ConnectionManager()

    websocket = AsyncMock()
    await mgr.connect(websocket, "test_client")
    await mgr.subscribe("test_client", "stock:quotes:000001")
    assert "stock:quotes:000001" in mgr.connection_subscriptions["test_client"]


@pytest.mark.asyncio
async def test_websocket_unsubscribe_message():
    """测试WebSocket取消订阅消息处理"""
    mgr = ConnectionManager()

    websocket = AsyncMock()
    await mgr.connect(websocket, "test_client")
    await mgr.subscribe("test_client", "stock:quotes:000001")
    await mgr.unsubscribe("test_client", "stock:quotes:000001")
    assert "stock:quotes:000001" not in mgr.connection_subscriptions["test_client"]


@pytest.mark.asyncio
async def test_websocket_ping_message():
    """测试WebSocket ping消息处理"""
    pass


@pytest.mark.asyncio
async def test_websocket_invalid_message():
    """测试WebSocket无效消息处理"""
    pass


# ===========================
# Integration Tests
# ===========================

@pytest.mark.asyncio
async def test_websocket_full_lifecycle():
    """测试WebSocket完整生命周期"""
    mgr = ConnectionManager()

    websocket = AsyncMock()

    # 1. 连接
    await mgr.connect(websocket, "test_client")
    assert "test_client" in mgr.active_connections

    # 2. 订阅
    await mgr.subscribe("test_client", "stock:quotes:000001")
    assert "stock:quotes:000001" in mgr.connection_subscriptions["test_client"]

    # 3. 接收广播
    quote_message = {
        "type": "quote",
        "symbol": "000001",
        "data": {"price": 10.50}
    }
    await mgr.broadcast(quote_message, "stock:quotes:000001")
    assert websocket.send_json.called

    # 4. 取消订阅
    await mgr.unsubscribe("test_client", "stock:quotes:000001")
    assert "stock:quotes:000001" not in mgr.connection_subscriptions["test_client"]

    # 5. 断开连接
    mgr.disconnect("test_client")
    assert "test_client" not in mgr.active_connections


@pytest.mark.asyncio
async def test_multiple_clients_same_subscription():
    """测试多个客户端订阅相同标的"""
    mgr = ConnectionManager()

    websocket1 = AsyncMock()
    websocket2 = AsyncMock()
    websocket3 = AsyncMock()

    await mgr.connect(websocket1, "client_1")
    await mgr.connect(websocket2, "client_2")
    await mgr.connect(websocket3, "client_3")

    for cid in ["client_1", "client_2", "client_3"]:
        await mgr.subscribe(cid, "stock:quotes:000001")

    message = {
        "type": "quote",
        "symbol": "000001",
        "data": {"price": 10.50}
    }

    await mgr.broadcast(message, "stock:quotes:000001")

    assert websocket1.send_json.called
    assert websocket2.send_json.called
    assert websocket3.send_json.called


@pytest.mark.asyncio
async def test_client_with_multiple_subscriptions():
    """测试客户端订阅多个标的"""
    mgr = ConnectionManager()

    websocket = AsyncMock()

    await mgr.connect(websocket, "test_client")
    await mgr.subscribe("test_client", "stock:quotes:000001")
    await mgr.subscribe("test_client", "stock:quotes:600000")
    await mgr.subscribe("test_client", "stock:quotes:000002")

    message1 = {
        "type": "quote",
        "symbol": "000001",
        "data": {"price": 10.50}
    }
    await mgr.broadcast(message1, "stock:quotes:000001")
    assert websocket.send_json.called

    websocket.send_json.reset_mock()

    message2 = {
        "type": "quote",
        "symbol": "000002",
        "data": {"price": 20.50}
    }
    await mgr.broadcast(message2, "stock:quotes:000002")
    assert websocket.send_json.called


@pytest.mark.asyncio
async def test_disconnect_clears_subscriptions():
    """测试断开连接清除订阅"""
    mgr = ConnectionManager()

    websocket = AsyncMock()

    await mgr.connect(websocket, "test_client")
    await mgr.subscribe("test_client", "stock:quotes:000001")
    await mgr.subscribe("test_client", "stock:quotes:600000")

    assert "test_client" in mgr.connection_subscriptions
    assert len(mgr.connection_subscriptions["test_client"]) == 2

    mgr.disconnect("test_client")

    assert "test_client" not in mgr.connection_subscriptions
    assert "test_client" not in mgr.active_connections
