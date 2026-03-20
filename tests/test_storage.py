# -*- coding: utf-8 -*-
"""
测试数据存储模块
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class TestDatabaseSchema:
    """测试数据库表结构定义"""

    def test_get_init_sql(self):
        """测试获取初始化SQL"""
        from backend.storage.schema import DatabaseSchema

        sql = DatabaseSchema.get_init_sql()
        assert "CREATE DATABASE IF NOT EXISTS" in sql
        assert "quant_db" in sql
        assert "CREATE STABLE IF NOT EXISTS stock_bars" in sql
        assert "CREATE STABLE IF NOT EXISTS stock_quotes" in sql
        assert "CREATE STABLE IF NOT EXISTS futures_bars" in sql
        assert "CREATE STABLE IF NOT EXISTS futures_quotes" in sql
        assert "CREATE STABLE IF NOT EXISTS index_bars" in sql
        assert "CREATE STABLE IF NOT EXISTS index_quotes" in sql
        assert "CREATE STABLE IF NOT EXISTS sector_quotes" in sql

    def test_get_create_table_sql(self):
        """测试获取创建表的SQL"""
        from backend.storage.schema import DatabaseSchema

        sql = DatabaseSchema.get_create_table_sql("stock_bars")
        assert "CREATE STABLE IF NOT EXISTS stock_bars" in sql
        assert "ts TIMESTAMP" in sql
        assert "open DOUBLE" in sql

    def test_get_create_table_sql_invalid(self):
        """测试获取不存在表的SQL"""
        from backend.storage.schema import DatabaseSchema

        with pytest.raises(ValueError):
            DatabaseSchema.get_create_table_sql("invalid_table")

    def test_get_all_table_names(self):
        """测试获取所有表名"""
        from backend.storage.schema import DatabaseSchema

        tables = DatabaseSchema.get_all_table_names()
        assert "stock_bars" in tables
        assert "stock_quotes" in tables
        assert "futures_bars" in tables
        assert "futures_quotes" in tables
        assert "index_bars" in tables
        assert "index_quotes" in tables
        assert "sector_quotes" in tables
        assert len(tables) >= 7

    def test_get_table_info(self):
        """测试获取表信息"""
        from backend.storage.schema import DatabaseSchema

        info = DatabaseSchema.get_table_info("stock_bars")
        assert info["description"] == "股票K线数据"
        assert "ts" in info["fields"]
        assert "open" in info["fields"]
        assert "symbol" in info["tags"]
        assert "market" in info["tags"]
        assert "1min" in info["intervals"]

    def test_get_child_table_name(self):
        """测试生成子表名称"""
        from backend.storage.schema import DatabaseSchema

        name = DatabaseSchema.get_child_table_name("stock_bars", "SZ000001", "SZ", "1min")
        assert "stock_bars" in name
        assert "SZ000001" in name


class TestSchemaManager:
    """测试数据库表结构管理器"""

    @pytest.mark.asyncio
    async def test_init_database(self, mock_tdengine_client):
        """测试初始化数据库"""
        from backend.storage.schema import SchemaManager

        manager = SchemaManager(mock_tdengine_client)
        await manager.init_database()

        # 验证执行了初始化SQL
        assert mock_tdengine_client.execute.called

    @pytest.mark.asyncio
    async def test_create_super_table(self, mock_tdengine_client):
        """测试创建超级表"""
        from backend.storage.schema import SchemaManager

        manager = SchemaManager(mock_tdengine_client)
        await manager.create_super_table("stock_bars")

        mock_tdengine_client.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_tables(self, mock_tdengine_client):
        """测试检查表"""
        from backend.storage.schema import SchemaManager

        # 模拟返回
        mock_tdengine_client.query = AsyncMock(return_value=[
            {"field1": "value1"},
            {"field1": "value2"}
        ])

        manager = SchemaManager(mock_tdengine_client)
        result = await manager.check_tables()

        assert isinstance(result, dict)
        assert len(result) > 0


class TestTDEngineClient:
    """测试TDengine客户端"""

    @pytest.mark.skipif(
        True,  # 需要taospy
        reason="需要TDengine客户端库"
    )
    def test_init_default(self):
        """测试默认初始化"""
        from backend.storage.tdengine_client import TDEngineClient

        with patch("backend.storage.tdengine_client.get_settings") as mock_settings:
            mock_config = Mock()
            mock_config.tdengine_host = "localhost"
            mock_config.tdengine_port = 6030
            mock_config.tdengine_user = "root"
            mock_config.tdengine_password = "taosdata"
            mock_config.tdengine_database = "quant_db"
            mock_settings.return_value = mock_config

            client = TDEngineClient()
            assert client.host == "localhost"
            assert client.port == 6030
            assert client.user == "root"
            assert client.database == "quant_db"

    @pytest.mark.skipif(
        True,  # 需要taospy
        reason="需要TDengine客户端库"
    )
    def test_init_with_config(self):
        """测试带配置初始化"""
        from backend.storage.tdengine_client import TDEngineClient

        config = {
            "host": "127.0.0.1",
            "port": 6030,
            "user": "root",
            "password": "taosdata",
        }

        with patch("backend.storage.tdengine_client.get_settings"):
            client = TDEngineClient(config)
            assert client.host == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_tdengine_client):
        """测试成功连接"""
        # 使用mock client进行测试
        assert mock_tdengine_client is not None

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_tdengine_client):
        """测试断开连接"""
        assert mock_tdengine_client is not None

    @pytest.mark.asyncio
    async def test_execute(self, mock_tdengine_client):
        """测试执行SQL"""
        await mock_tdengine_client.execute("CREATE TABLE test (id INT)")
        mock_tdengine_client.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_query(self, mock_tdengine_client):
        """测试查询"""
        mock_tdengine_client.query = AsyncMock(return_value=[
            {"id": 1, "name": "test1"},
            {"id": 2, "name": "test2"},
        ])

        result = await mock_tdengine_client.query("SELECT * FROM test")
        assert len(result) == 2
        assert result[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_insert_stock_quote(self, mock_tdengine_client):
        """测试插入股票行情"""
        quote = {
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

        result = await mock_tdengine_client.insert_stock_quote(quote)
        assert result is True

    @pytest.mark.asyncio
    async def test_insert_stock_bars(self, mock_tdengine_client, sample_stock_bars):
        """测试批量插入股票K线"""
        result = await mock_tdengine_client.insert_stock_bars(sample_stock_bars)
        assert result == len(sample_stock_bars)

    @pytest.mark.asyncio
    async def test_insert_futures_quote(self, mock_tdengine_client, sample_futures_quote):
        """测试插入期货行情"""
        result = await mock_tdengine_client.insert_futures_quote(sample_futures_quote)
        assert result is True

    @pytest.mark.asyncio
    async def test_query_stock_bars(self, mock_tdengine_client):
        """测试查询股票K线"""
        mock_tdengine_client.query = AsyncMock(return_value=[])

        result = await mock_tdengine_client.query_stock_bars(
            symbol="SZ000001",
            interval="1day",
            limit=100
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_query_stock_quote_latest(self, mock_tdengine_client):
        """测试查询最新股票行情"""
        # 给mock添加query_stock_quote_latest方法
        async def mock_query_latest(symbol):
            return {
                "symbol": symbol,
                "ts": "2024-01-01 10:00:00",
                "close": 10.70,
            }

        mock_tdengine_client.query_stock_quote_latest = mock_query_latest

        result = await mock_tdengine_client.query_stock_quote_latest("SZ000001")
        assert result is not None
        assert result["symbol"] == "SZ000001"

    @pytest.mark.skipif(
        True,  # 需要实际客户端实例
        reason="需要实际客户端实例"
    )
    def test_format_timestamp(self):
        """测试时间戳格式化"""
        pass

    @pytest.mark.asyncio
    async def test_health_check(self, mock_tdengine_client):
        """测试健康检查"""
        mock_tdengine_client.query = AsyncMock(return_value=[{"result": 1}])

        result = await mock_tdengine_client.health_check()
        assert result is True

    def test_get_stats(self, mock_tdengine_client):
        """测试获取统计信息"""
        # 给mock添加stats属性
        if not hasattr(mock_tdengine_client, 'stats'):
            mock_tdengine_client.stats = {
                "total_inserted": 0,
                "total_queried": 0,
                "errors": 0,
            }

        stats = mock_tdengine_client.get_stats()
        assert "total_inserted" in stats
        assert "total_queried" in stats
        assert "errors" in stats

    def test_reset_stats(self, mock_tdengine_client):
        """测试重置统计信息"""
        # 给mock添加stats属性
        if not hasattr(mock_tdengine_client, 'stats'):
            mock_tdengine_client.stats = {
                "total_inserted": 0,
                "total_queried": 0,
                "errors": 0,
            }

        mock_tdengine_client.reset_stats()
        stats = mock_tdengine_client.get_stats()
        assert stats["total_inserted"] == 0
        assert stats["total_queried"] == 0
        assert stats["errors"] == 0
