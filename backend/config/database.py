# -*- coding: utf-8 -*-
"""
数据库配置
"""
from typing import Optional
from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    """TDengine数据库配置"""

    # 连接配置
    host: str = "tdengine"
    port: int = 6030
    user: str = "root"
    password: str = "taosdata"
    database: str = "quant_db"

    # 连接池配置
    max_connections: int = 50
    min_connections: int = 5
    connection_timeout: int = 10

    # 查询配置
    query_timeout: int = 30
    max_query_results: int = 100000

    # 写入配置
    batch_size: int = 1000
    batch_timeout: int = 5
    max_retries: int = 3

    # 数据保留配置
    keep_duration: str = "3650 days"  # 10年

    # 表配置
    super_table_stock_bars: str = "stock_bars"
    super_table_stock_quotes: str = "stock_quotes"
    super_table_stock_ticks: str = "stock_ticks"
    super_table_futures_bars: str = "futures_bars"
    super_table_futures_quotes: str = "futures_quotes"
    super_table_futures_ticks: str = "futures_ticks"
    super_table_index_bars: str = "index_bars"
    super_table_index_quotes: str = "index_quotes"
    super_table_sector_quotes: str = "sector_quotes"


# 默认配置
default_db_config = DatabaseConfig()
