# -*- coding: utf-8 -*-
"""
配置管理模块
"""
from .settings import settings, get_settings
from .database import DatabaseConfig

__all__ = ["settings", "get_settings", "DatabaseConfig"]
