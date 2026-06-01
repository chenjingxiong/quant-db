# -*- coding: utf-8 -*-
"""
PostgreSQL数据库模块

提供PostgreSQL数据库连接和操作接口
"""
from .postgres_client import PostgresClient, get_postgres_client

__all__ = [
    "PostgresClient",
    "get_postgres_client",
]
