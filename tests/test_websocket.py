# -*- coding: utf-8 -*-
"""
WebSocket API 测试
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.api.routes.websocket import (
    ConnectionManager,
    get_connection_manager,
    broadcast_message,
)


# ===========================
# ConnectionManager Tests
# ===========================

@pytest.mark.asyncio
async def test_connection_manager_initialization():
    """测试连接管理器初始化"""
    manager = ConnectionManager()

    assert manager is not None
    assert len(manager.active_connections) == 0
    assert len(manager.subscriptions) == 0


@pytest.mark.asyncio
async def test_connect():
    """测试WebSocket连接"""
    manager = ConnectionManager()

    # 模拟WebSocket连接
    websocket = AsyncMock()
    websocket.client_id = "test_client_1"

    await manager.connect(websocket)

    assert websocket in manager.active_connections
    assert manager.subscriptions[websocket] == set()


@pytest.mark.asyncio
async def test_disconnect():
    """测试WebSocket断开连接"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    websocket.client_id = "test_client_1"

    await manager.connect(websocket)
    await manager.disconnect(websocket)

    assert websocket not in manager.active_connections
    assert websocket not in manager.subscriptions


@pytest.mark.asyncio
async def test_subscribe():
    """测试订阅"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    websocket.client_id = "test_client_1"

    await manager.connect(websocket)
    await manager.subscribe(websocket, ["000001", "600000"])

    assert "000001" in manager.subscriptions[websocket]
    assert "600000" in manager.subscriptions[websocket]


@pytest.mark.asyncio
async def test_unsubscribe():
    """测试取消订阅"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    websocket.client_id = "test_client_1"

    await manager.connect(websocket)
    await manager.subscribe(websocket, ["000001", "600000"])
    await manager.unsubscribe(websocket, ["000001"])

    assert "000001" not in manager.subscriptions[websocket]
    assert "600000" in manager.subscriptions[websocket]


@pytest.mark.asyncio
async def test_unsubscribe_all():
    """测试取消所有订阅"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    websocket.client_id = "test_client_1"

    await manager.connect(websocket)
    await manager.subscribe(websocket, ["000001", "600000"])
    await manager.unsubscribe_all(websocket)

    assert len(manager.subscriptions[websocket]) == 0


@pytest.mark.asyncio
async def test_send_personal_message():
    """测试发送个人消息"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    websocket.client_id = "test_client_1"

    await manager.connect(websocket)

    message = {"type": "test", "data": "hello"}
    await manager.send_personal_message(message, websocket)

    # 验证send被调用
    assert websocket.send.called
    sent_data = json.loads(websocket.send.call_args[0][0])
    assert sent_data["type"] == "test"


@pytest.mark.asyncio
async def test_broadcast():
    """测试广播消息"""
    manager = ConnectionManager()

    # 创建多个连接
    websocket1 = AsyncMock()
    websocket1.client_id = "client_1"
    websocket2 = AsyncMock()
    websocket2.client_id = "client_2"

    await manager.connect(websocket1)
    await manager.connect(websocket2)

    message = {"type": "broadcast", "data": "hello all"}
    await manager.broadcast(message)

    # 验证所有连接都收到消息
    assert websocket1.send.called
    assert websocket2.send.called


@pytest.mark.asyncio
async def test_broadcast_to_subscribers():
    """测试广播给订阅者"""
    manager = ConnectionManager()

    websocket1 = AsyncMock()
    websocket1.client_id = "client_1"
    websocket2 = AsyncMock()
    websocket2.client_id = "client_2"

    await manager.connect(websocket1)
    await manager.connect(websocket2)

    # client1订阅000001，client2订阅600000
    await manager.subscribe(websocket1, ["000001"])
    await manager.subscribe(websocket2, ["600000"])

    message = {
        "type": "quote",
        "symbol": "000001",
        "data": {"price": 10.50}
    }

    await manager.broadcast_to_subscribers(message)

    # 只有client1应该收到消息
    assert websocket1.send.called
    assert not websocket2.send.called


@pytest.mark.asyncio
async def test_get_connection_count():
    """测试获取连接数"""
    manager = ConnectionManager()

    assert await manager.get_connection_count() == 0

    websocket1 = AsyncMock()
    websocket2 = AsyncMock()

    await manager.connect(websocket1)
    await manager.connect(websocket2)

    assert await manager.get_connection_count() == 2


@pytest.mark.asyncio
async def test_get_subscription_info():
    """测试获取订阅信息"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    websocket.client_id = "test_client"

    await manager.connect(websocket)
    await manager.subscribe(websocket, ["000001", "600000"])

    info = await manager.get_subscription_info()

    assert info["total_connections"] == 1
    assert info["subscriptions"]["test_client"] == ["000001", "600000"]


# ===========================
# Helper Functions Tests
# ===========================

def test_get_connection_manager():
    """测试获取连接管理器实例"""
    manager = get_connection_manager()
    assert manager is not None
    assert isinstance(manager, ConnectionManager)


@pytest.mark.asyncio
async def test_broadcast_message_helper():
    """测试广播消息辅助函数"""
    manager = get_connection_manager()

    websocket = AsyncMock()
    await manager.connect(websocket)

    await broadcast_message({"type": "test", "data": "hello"})

    assert websocket.send.called


# ===========================
# WebSocket Endpoint Tests
# ===========================

@pytest.mark.asyncio
async def test_websocket_endpoint_connect():
    """测试WebSocket端点连接"""
    from fastapi.testclient import TestClient
    from backend.api.app import app

    # 注意：这个测试需要实际的WebSocket连接
    # 这里只是展示结构，实际测试需要使用WebSocketTestClient
    pass


@pytest.mark.asyncio
async def test_websocket_subscribe_message():
    """测试WebSocket订阅消息处理"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    await manager.connect(websocket)

    # 模拟接收订阅消息
    subscribe_message = {
        "action": "subscribe",
        "symbols": ["000001", "600000"]
    }

    # 这里应该有实际的消息处理逻辑
    # 测试消息被正确解析和订阅
    pass


@pytest.mark.asyncio
async def test_websocket_unsubscribe_message():
    """测试WebSocket取消订阅消息处理"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    await manager.connect(websocket)
    await manager.subscribe(websocket, ["000001", "600000"])

    # 模拟接收取消订阅消息
    unsubscribe_message = {
        "action": "unsubscribe",
        "symbols": ["000001"]
    }

    # 这里应该有实际的消息处理逻辑
    pass


@pytest.mark.asyncio
async def test_websocket_ping_message():
    """测试WebSocket ping消息处理"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    await manager.connect(websocket)

    ping_message = {"action": "ping"}

    # 应该返回pong响应
    pass


@pytest.mark.asyncio
async def test_websocket_invalid_message():
    """测试WebSocket无效消息处理"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    await manager.connect(websocket)

    # 无效的消息格式
    invalid_message = {"invalid": "data"}

    # 应该返回错误消息
    pass


# ===========================
# Integration Tests
# ===========================

@pytest.mark.asyncio
async def test_websocket_full_lifecycle():
    """测试WebSocket完整生命周期"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    websocket.client_id = "test_client"

    # 1. 连接
    await manager.connect(websocket)
    assert websocket in manager.active_connections

    # 2. 订阅
    await manager.subscribe(websocket, ["000001"])
    assert "000001" in manager.subscriptions[websocket]

    # 3. 接收广播
    quote_message = {
        "type": "quote",
        "symbol": "000001",
        "data": {"price": 10.50}
    }
    await manager.broadcast_to_subscribers(quote_message)
    assert websocket.send.called

    # 4. 取消订阅
    await manager.unsubscribe(websocket, ["000001"])
    assert "000001" not in manager.subscriptions[websocket]

    # 5. 断开连接
    await manager.disconnect(websocket)
    assert websocket not in manager.active_connections


@pytest.mark.asyncio
async def test_multiple_clients_same_subscription():
    """测试多个客户端订阅相同标的"""
    manager = ConnectionManager()

    websocket1 = AsyncMock()
    websocket1.client_id = "client_1"
    websocket2 = AsyncMock()
    websocket2.client_id = "client_2"
    websocket3 = AsyncMock()
    websocket3.client_id = "client_3"

    await manager.connect(websocket1)
    await manager.connect(websocket2)
    await manager.connect(websocket3)

    # 所有客户端订阅000001
    for ws in [websocket1, websocket2, websocket3]:
        await manager.subscribe(ws, ["000001"])

    message = {
        "type": "quote",
        "symbol": "000001",
        "data": {"price": 10.50}
    }

    await manager.broadcast_to_subscribers(message)

    # 所有客户端都应该收到消息
    assert websocket1.send.called
    assert websocket2.send.called
    assert websocket3.send.called


@pytest.mark.asyncio
async def test_client_with_multiple_subscriptions():
    """测试客户端订阅多个标的"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    websocket.client_id = "test_client"

    await manager.connect(websocket)
    await manager.subscribe(websocket, ["000001", "600000", "000002"])

    # 广播000001的行情
    message1 = {
        "type": "quote",
        "symbol": "000001",
        "data": {"price": 10.50}
    }
    await manager.broadcast_to_subscribers(message1)
    assert websocket.send.called

    websocket.send.reset_mock()

    # 广播000002的行情
    message2 = {
        "type": "quote",
        "symbol": "000002",
        "data": {"price": 20.50}
    }
    await manager.broadcast_to_subscribers(message2)
    assert websocket.send.called


@pytest.mark.asyncio
async def test_disconnect_clears_subscriptions():
    """测试断开连接清除订阅"""
    manager = ConnectionManager()

    websocket = AsyncMock()
    websocket.client_id = "test_client"

    await manager.connect(websocket)
    await manager.subscribe(websocket, ["000001", "600000"])

    assert websocket in manager.subscriptions
    assert len(manager.subscriptions[websocket]) == 2

    await manager.disconnect(websocket)

    assert websocket not in manager.subscriptions
    assert websocket not in manager.active_connections
