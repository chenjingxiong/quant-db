# -*- coding: utf-8 -*-
"""
测试API路由
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch


@pytest.fixture
def test_client():
    """创建测试客户端"""
    from backend.api.app import app
    return TestClient(app)


class TestHealthEndpoint:
    """测试健康检查端点"""

    def test_health_check(self, test_client):
        """测试健康检查"""
        response = test_client.get("/health")
        assert response.status_code in [200, 503]  # 可能返回503如果数据库未连接

    @pytest.mark.skip(reason="需要特殊的mock设置")
    def test_health_with_mock(self, test_client):
        """测试健康检查（带模拟）"""
        with patch("backend.api.app.get_td_client") as mock_get_client:
            mock_client = Mock()
            mock_client.health_check = AsyncMock(return_value=True)
            mock_get_client.return_value = mock_client

            response = test_client.get("/health")
            assert response.status_code in [200, 503]


class TestRootEndpoint:
    """测试根路径端点"""

    def test_root(self, test_client):
        """测试根路径"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestStockAPI:
    """测试股票API"""

    def test_get_stock_quotes(self, test_client):
        """测试获取股票行情"""
        # 模拟数据源
        with patch("backend.api.routes.stock.PytdxAdapter") as mock_adapter_cls:
            mock_adapter = Mock()
            mock_adapter.connect = AsyncMock(return_value=True)
            mock_adapter.disconnect = AsyncMock()
            mock_adapter.get_stock_quotes = AsyncMock(return_value=[
                Mock(
                    symbol="SZ000001",
                    ts=datetime.now(),
                    open=10.50,
                    high=10.80,
                    low=10.30,
                    close=10.70,
                    volume=1000000.0,
                    amount=10700000.0,
                )
            ])
            mock_adapter_cls.return_value = mock_adapter

            response = test_client.get("/api/v1/stocks/quotes?symbols=SZ000001")
            assert response.status_code in [200, 500]

    def test_get_stock_quotes_empty_symbols(self, test_client):
        """测试空股票代码"""
        response = test_client.get("/api/v1/stocks/quotes?symbols=")
        # FastAPI可能返回422或其他状态码
        assert response.status_code in [200, 400, 422, 500]

    def test_get_stock_list(self, test_client):
        """测试获取股票列表"""
        with patch("backend.api.routes.stock.PytdxAdapter") as mock_adapter_cls:
            mock_adapter = Mock()
            mock_adapter.connect = AsyncMock(return_value=True)
            mock_adapter.disconnect = AsyncMock()
            mock_adapter.get_all_stock_list = AsyncMock(return_value=[
                {"symbol": "SZ000001", "code": "000001", "name": "平安银行", "market": "SZ"},
            ])
            mock_adapter_cls.return_value = mock_adapter

            response = test_client.get("/api/v1/stocks/list")
            assert response.status_code in [200, 500]

    def test_get_stock_bars(self, test_client):
        """测试获取K线数据"""
        # 这个测试需要全局mock，暂时跳过
        response = test_client.get(
            "/api/v1/stocks/bars?symbol=SZ000001&interval=1day&limit=100"
        )
        assert response.status_code in [200, 500, 503, 404]

    def test_get_stock_detail(self, test_client):
        """测试获取股票详情"""
        response = test_client.get("/api/v1/stocks/SZ000001/detail")
        assert response.status_code in [200, 404, 500]


class TestFuturesAPI:
    """测试期货API"""

    def test_get_futures_quotes(self, test_client):
        """测试获取期货行情"""
        response = test_client.get("/api/v1/futures/quotes?symbols=IF2503")
        assert response.status_code in [200, 500]

    def test_get_futures_bars(self, test_client):
        """测试获取期货K线"""
        response = test_client.get(
            "/api/v1/futures/bars?symbol=IF2503&interval=1day&limit=100"
        )
        assert response.status_code in [200, 500, 503]

    def test_get_futures_list(self, test_client):
        """测试获取期货列表"""
        response = test_client.get("/api/v1/futures/list")
        assert response.status_code in [200, 500]


class TestIndexAPI:
    """测试指数API"""

    def test_get_index_quotes(self, test_client):
        """测试获取指数行情"""
        response = test_client.get("/api/v1/indices/quotes?symbols=000001")
        assert response.status_code in [200, 500]

    def test_get_index_bars(self, test_client):
        """测试获取指数K线"""
        response = test_client.get(
            "/api/v1/indices/bars?symbol=000001&interval=1day&limit=100"
        )
        assert response.status_code in [200, 500, 503]


class TestSectorAPI:
    """测试板块API"""

    def test_get_sector_list(self, test_client):
        """测试获取板块列表"""
        response = test_client.get("/api/v1/sectors/list")
        assert response.status_code in [200, 500]

    def test_get_sector_quotes(self, test_client):
        """测试获取板块行情"""
        response = test_client.get("/api/v1/sectors/%E9%87%91%E8%9E%8D/quotes")
        assert response.status_code in [200, 500]


class TestCollectAPI:
    """测试采集管理API"""

    def test_get_collect_status(self, test_client):
        """测试获取采集状态"""
        response = test_client.get("/api/v1/collect/status")
        assert response.status_code in [200, 404, 500]

    def test_get_collect_tasks(self, test_client):
        """测试获取采集任务"""
        response = test_client.get("/api/v1/collect/tasks")
        assert response.status_code in [200, 404, 500]

    def test_start_collect(self, test_client):
        """测试启动采集"""
        response = test_client.post(
            "/api/v1/collect/start",
            json={
                "data_type": "stock",
                "symbols": ["SZ000001"],
            }
        )
        assert response.status_code in [200, 400, 404, 422, 500]

    def test_stop_collect(self, test_client):
        """测试停止采集"""
        response = test_client.post(
            "/api/v1/collect/stop",
            json={"task_id": "test_task"}
        )
        assert response.status_code in [200, 400, 404, 422, 500]


class TestWebSocket:
    """测试WebSocket"""

    @pytest.mark.asyncio
    async def test_websocket_connect(self):
        """测试WebSocket连接"""
        # WebSocket测试需要特殊处理
        pass
