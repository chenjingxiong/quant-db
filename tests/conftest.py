# -*- coding: utf-8 -*-
"""
pytest 配置和共享 fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """模拟配置"""
    from backend.config import Settings

    return Settings(
        tdengine_host="localhost",
        tdengine_port=6030,
        tdengine_user="root",
        tdengine_password="taosdata",
        tdengine_database="test_quant_db",
        pytdx_hosts="119.147.212.81",
        pytdx_port=7709,
        collect_interval=5,
        max_retry=3,
        batch_size=1000,
        cache_size=1000,
        api_host="127.0.0.1",
        api_port=8000,
        api_workers=1,
        log_level="DEBUG",
    )


@pytest.fixture
def sample_stock_quote():
    """示例股票行情数据"""
    return {
        "symbol": "SZ000001",
        "ts": datetime.now(),
        "open": 10.50,
        "high": 10.80,
        "low": 10.30,
        "close": 10.70,
        "pre_close": 10.40,
        "volume": 1000000.0,
        "amount": 10700000.0,
        "change": 0.30,
        "change_percent": 2.88,
        "bid_price1": 10.68,
        "bid_volume1": 10000,
        "ask_price1": 10.71,
        "ask_volume1": 5000,
    }


@pytest.fixture
def sample_stock_bars():
    """示例股票K线数据"""
    bars = []
    base_time = datetime.now()
    for i in range(10):
        bars.append({
            "symbol": "SZ000001",
            "interval": "1min",
            "ts": base_time,
            "open": 10.50 + i * 0.01,
            "high": 10.80 + i * 0.01,
            "low": 10.30 + i * 0.01,
            "close": 10.70 + i * 0.01,
            "volume": 1000000.0 + i * 1000,
            "amount": 10700000.0 + i * 10000,
        })
    return bars


@pytest.fixture
def sample_futures_quote():
    """示例期货行情数据"""
    return {
        "symbol": "IF2503",
        "ts": datetime.now(),
        "open": 3500.0,
        "high": 3550.0,
        "low": 3480.0,
        "close": 3520.0,
        "pre_close": 3490.0,
        "settlement": 3510.0,
        "volume": 50000.0,
        "amount": 175000000.0,
        "open_interest": 100000.0,
        "change": 30.0,
        "change_percent": 0.86,
    }


@pytest.fixture
def sample_futures_bars():
    """示例期货K线数据"""
    bars = []
    base_time = datetime.now()
    for i in range(10):
        bars.append({
            "symbol": "IF2503",
            "interval": "1min",
            "ts": base_time,
            "open": 3500.0 + i * 5,
            "high": 3550.0 + i * 5,
            "low": 3480.0 + i * 5,
            "close": 3520.0 + i * 5,
            "volume": 50000.0 + i * 100,
            "amount": 175000000.0 + i * 1000,
            "open_interest": 100000.0 + i * 10,
            "settlement": 3510.0 + i * 5,
        })
    return bars


@pytest.fixture
def mock_tdengine_client():
    """模拟TDengine客户端"""
    client = Mock()
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    client.execute = AsyncMock(return_value=None)
    client.query = AsyncMock(return_value=[])
    client.insert_stock_quote = AsyncMock(return_value=True)
    client.insert_stock_bars = AsyncMock(return_value=10)
    client.insert_futures_quote = AsyncMock(return_value=True)
    client.query_stock_bars = AsyncMock(return_value=[])
    client.query_stock_quote_latest = AsyncMock(return_value=None)
    client.health_check = AsyncMock(return_value=True)
    client.use_database = AsyncMock()

    # 添加stats和methods
    client.stats = {
        "total_inserted": 0,
        "total_queried": 0,
        "errors": 0,
    }

    def get_stats():
        return client.stats

    def reset_stats():
        client.stats = {
            "total_inserted": 0,
            "total_queried": 0,
            "errors": 0,
        }

    client.get_stats = get_stats
    client.reset_stats = reset_stats

    return client


@pytest.fixture
def mock_adapter():
    """模拟数据源适配器"""
    from backend.adapters.base import Quote, Bar

    adapter = Mock()
    adapter.connect = AsyncMock(return_value=True)
    adapter.disconnect = AsyncMock()
    adapter.health_check = AsyncMock(return_value=True)
    adapter.is_connected = True
    adapter.name = "MockAdapter"

    # 模拟获取股票行情
    async def mock_get_stock_quotes(symbols):
        return [Quote(
            symbol=s,
            ts=datetime.now(),
            open=10.50,
            high=10.80,
            low=10.30,
            close=10.70,
            volume=1000000.0,
            amount=10700000.0,
        ) for s in symbols]

    # 模拟获取期货行情
    async def mock_get_futures_quotes(symbols):
        return [Quote(
            symbol=s,
            ts=datetime.now(),
            open=3500.0,
            high=3550.0,
            low=3480.0,
            close=3520.0,
            volume=50000.0,
            amount=175000000.0,
        ) for s in symbols]

    # 模拟获取K线
    async def mock_get_stock_bars(symbol, interval, start_time, end_time, limit):
        return [Bar(
            symbol=symbol,
            interval=interval,
            ts=datetime.now(),
            open=10.50,
            high=10.80,
            low=10.30,
            close=10.70,
            volume=1000000.0,
            amount=10700000.0,
        ) for _ in range(min(limit, 10))]

    adapter.get_stock_quotes = mock_get_stock_quotes
    adapter.get_futures_quotes = mock_get_futures_quotes
    adapter.get_stock_bars = mock_get_stock_bars
    adapter.get_futures_bars = mock_get_stock_bars

    return adapter
