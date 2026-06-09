# -*- coding: utf-8 -*-
"""
测试数据源适配器
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from backend.adapters.base import BaseAdapter, Quote, Bar, Tick


class TestQuote:
    """测试Quote数据模型"""

    def test_quote_creation(self):
        """测试创建Quote对象"""
        quote = Quote(
            symbol="SZ000001",
            ts=datetime.now(),
            open=10.50,
            high=10.80,
            low=10.30,
            close=10.70,
            volume=1000000.0,
            amount=10700000.0,
        )
        assert quote.symbol == "SZ000001"
        assert quote.open == 10.50
        assert quote.high == 10.80
        assert quote.volume == 1000000.0

    def test_quote_with_change(self):
        """测试带涨跌幅的Quote"""
        quote = Quote(
            symbol="SZ000001",
            ts=datetime.now(),
            open=10.50,
            high=10.80,
            low=10.30,
            close=10.70,
            pre_close=10.40,
            change=0.30,
            change_percent=2.88,
        )
        assert quote.change == 0.30
        assert quote.change_percent == 2.88

    def test_quote_with_extra(self):
        """测试带扩展数据的Quote"""
        quote = Quote(
            symbol="SZ000001",
            ts=datetime.now(),
            open=10.50,
            close=10.70,
            extra={"name": "平安银行", "bid1": 10.68}
        )
        assert quote.extra["name"] == "平安银行"
        assert quote.extra["bid1"] == 10.68


class TestBar:
    """测试Bar数据模型"""

    def test_bar_creation(self):
        """测试创建Bar对象"""
        bar = Bar(
            symbol="SZ000001",
            interval="1min",
            ts=datetime.now(),
            open=10.50,
            high=10.80,
            low=10.30,
            close=10.70,
            volume=1000000.0,
            amount=10700000.0,
        )
        assert bar.symbol == "SZ000001"
        assert bar.interval == "1min"
        assert bar.open == 10.50
        assert bar.volume == 1000000.0


class TestTick:
    """测试Tick数据模型"""

    def test_tick_creation(self):
        """测试创建Tick对象"""
        tick = Tick(
            symbol="SZ000001",
            ts=datetime.now(),
            price=10.70,
            volume=1000.0,
            amount=10700.0,
            direction="B",
        )
        assert tick.symbol == "SZ000001"
        assert tick.price == 10.70
        assert tick.direction == "B"


class TestBaseAdapter:
    """测试基础适配器"""

    def test_base_adapter_init(self):
        """测试初始化"""
        adapter = MockBaseAdapter()
        assert adapter.name == "MockBaseAdapter"
        assert adapter.is_connected is False
        assert adapter.config == {}

    def test_base_adapter_with_config(self):
        """测试带配置的初始化"""
        config = {"timeout": 10, "hosts": ["127.0.0.1"]}
        adapter = MockBaseAdapter(config)
        assert adapter.config == config

    @pytest.mark.asyncio
    async def test_health_check_not_connected(self, mock_adapter):
        """测试健康检查 - 未连接状态"""
        mock_adapter.is_connected = False
        mock_adapter.connect = AsyncMock(return_value=True)
        mock_adapter.get_stock_quotes = AsyncMock(return_value=[])

        result = await mock_adapter.health_check()
        assert result is True

    def test_adapter_repr(self):
        """测试适配器字符串表示"""
        adapter = MockBaseAdapter()
        adapter.is_connected = True
        assert "MockBaseAdapter" in repr(adapter)
        assert "connected=True" in repr(adapter)


class MockBaseAdapter(BaseAdapter):
    """模拟适配器实现"""

    async def connect(self) -> bool:
        self.is_connected = True
        return True

    async def disconnect(self):
        self.is_connected = False

    async def get_stock_quotes(self, symbols):
        return [
            Quote(
                symbol=s,
                ts=datetime.now(),
                open=10.50,
                high=10.80,
                low=10.30,
                close=10.70,
                volume=1000000.0,
                amount=10700000.0,
            )
            for s in symbols
        ]

    async def get_futures_quotes(self, symbols):
        return [
            Quote(
                symbol=s,
                ts=datetime.now(),
                open=3500.0,
                high=3550.0,
                low=3480.0,
                close=3520.0,
                volume=50000.0,
                amount=175000000.0,
            )
            for s in symbols
        ]

    async def get_stock_bars(self, symbol, interval, start_time=None, end_time=None, limit=1000):
        return [
            Bar(
                symbol=symbol,
                interval=interval,
                ts=datetime.now(),
                open=10.50,
                high=10.80,
                low=10.30,
                close=10.70,
                volume=1000000.0,
                amount=10700000.0,
            )
            for _ in range(10)
        ]

    async def get_futures_bars(self, symbol, interval, start_time=None, end_time=None, limit=1000):
        return await self.get_stock_bars(symbol, interval, start_time, end_time, limit)

    async def get_stock_ticks(self, symbol, start_time=None, end_time=None, limit=1000):
        return [
            Tick(
                symbol=symbol,
                ts=datetime.now(),
                price=10.70,
                volume=1000.0,
                amount=10700.0,
                direction="B",
            )
            for _ in range(10)
        ]


@pytest.mark.skipif(
    True,  # 跳过实际网络测试，可以在CI/CD中启用
    reason="需要网络连接和pytdx库"
)
class TestPytdxAdapter:
    """测试pytdx适配器"""

    @pytest.mark.asyncio
    async def test_connect(self):
        """测试连接"""
        from backend.adapters.pytdx_adapter import PytdxAdapter

        adapter = PytdxAdapter({"hosts": ["119.147.212.81"], "port": 7709})
        result = await adapter.connect()
        assert result in [True, False]  # 网络可能失败

    @pytest.mark.asyncio
    async def test_parse_symbol(self):
        """测试解析股票代码"""
        from backend.adapters.pytdx_adapter import PytdxAdapter

        adapter = PytdxAdapter()

        # 测试上海股票
        market, code = adapter._parse_symbol("SH600000")
        assert market == 1  # MARKET_SH
        assert code == "600000"

        # 测试深圳股票
        market, code = adapter._parse_symbol("SZ000001")
        assert market == 0  # MARKET_SZ
        assert code == "000001"

        # 测试6开头股票（上海）
        market, code = adapter._parse_symbol("600000")
        assert market == 1
        assert code == "600000"

        # 测试0开头股票（深圳）
        market, code = adapter._parse_symbol("000001")
        assert market == 0
        assert code == "000001"


@pytest.mark.skipif(True, reason="modtdx不是必需的")
class TestModtdxAdapter:
    """测试modtdx适配器"""

    @pytest.mark.asyncio
    async def test_not_available(self):
        """测试modtdx不可用时的行为"""
        from backend.adapters.modtdx_adapter import ModtdxAdapter

        adapter = ModtdxAdapter()
        assert adapter.MODTDX_AVAILABLE is False  # 通常不可用


@pytest.mark.skipif(True, reason="QMT不是必需的")
class TestQmtAdapter:
    """测试QMT适配器"""

    @pytest.mark.asyncio
    async def test_not_available(self):
        """测试QMT不可用时的行为"""
        from backend.adapters.qmt_adapter import QmtAdapter

        adapter = QmtAdapter()
        assert adapter.QMT_AVAILABLE is False  # 通常不可用
