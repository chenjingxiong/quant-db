# -*- coding: utf-8 -*-
"""
权限定义模块

定义系统权限和角色
"""
from enum import Enum
from typing import List, Dict


class Permission(Enum):
    """权限枚举"""

    # 数据查看权限
    STOCK_READ = "stock:read"
    FUTURES_READ = "futures:read"
    INDEX_READ = "index:read"
    SECTOR_READ = "sector:read"
    QUOTES_READ = "quotes:read"

    # 数据管理权限
    COLLECT_START = "collect:start"
    COLLECT_STOP = "collect:stop"
    COLLECT_CONFIG = "collect:config"
    COLLECT_VIEW = "collect:view"

    # 技术指标权限
    INDICATORS_VIEW = "indicators:view"
    INDICATORS_CALCULATE = "indicators:calculate"
    INDICATORS_MANAGE = "indicators:manage"

    # 选股权限
    SCREENER_VIEW = "screener:view"
    SCREENER_RUN = "screener:run"
    SCREENER_MANAGE = "screener:manage"

    # 组合管理权限
    PORTFOLIO_VIEW = "portfolio:view"
    PORTFOLIO_MANAGE = "portfolio:manage"
    PORTFOLIO_ANALYZE = "portfolio:analyze"

    # 回测权限
    BACKTEST_VIEW = "backtest:view"
    BACKTEST_RUN = "backtest:run"
    BACKTEST_MANAGE = "backtest:manage"

    # 用户管理权限
    USER_READ = "user:read"
    USER_MANAGE = "user:manage"
    USER_DELETE = "user:delete"

    # 系统管理权限
    SYSTEM_CONFIG = "system:config"
    LOGS_VIEW = "logs:view"
    METRICS_VIEW = "metrics:view"
    AUDIT_LOGS_VIEW = "audit:logs:view"

    # API管理权限
    APIKEY_CREATE = "apikey:create"
    APIKEY_MANAGE = "apikey:manage"
    APIKEY_DELETE = "apikey:delete"


class Role(Enum):
    """角色枚举"""

    ADMIN = "admin"  # 管理员
    TRADER = "trader"  # 交易员
    USER = "user"  # 普通用户
    GUEST = "guest"  # 访客


# 角色权限映射
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ADMIN: [
        # 管理员拥有所有权限
        *list(Permission),
    ],
    Role.TRADER: [
        # 交易员权限
        Permission.STOCK_READ,
        Permission.FUTURES_READ,
        Permission.INDEX_READ,
        Permission.SECTOR_READ,
        Permission.QUOTES_READ,
        Permission.COLLECT_VIEW,
        Permission.INDICATORS_VIEW,
        Permission.INDICATORS_CALCULATE,
        Permission.SCREENER_VIEW,
        Permission.SCREENER_RUN,
        Permission.PORTFOLIO_VIEW,
        Permission.PORTFOLIO_MANAGE,
        Permission.PORTFOLIO_ANALYZE,
        Permission.BACKTEST_VIEW,
        Permission.BACKTEST_RUN,
        Permission.USER_READ,
    ],
    Role.USER: [
        # 普通用户权限（只读）
        Permission.STOCK_READ,
        Permission.FUTURES_READ,
        Permission.INDEX_READ,
        Permission.SECTOR_READ,
        Permission.QUOTES_READ,
        Permission.COLLECT_VIEW,
        Permission.INDICATORS_VIEW,
        Permission.SCREENER_VIEW,
        Permission.PORTFOLIO_VIEW,
        Permission.BACKTEST_VIEW,
    ],
    Role.GUEST: [
        # 访客权限（基础只读）
        Permission.STOCK_READ,
        Permission.FUTURES_READ,
        Permission.INDEX_READ,
        Permission.QUOTES_READ,
    ],
}


def get_permissions_for_role(role: Role) -> List[Permission]:
    """
    获取角色对应的权限列表

    Args:
        role: 角色

    Returns:
        权限列表
    """
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(user_role: Role, required_permission: Permission) -> bool:
    """
    检查用户角色是否拥有指定权限

    Args:
        user_role: 用户角色
        required_permission: 需要的权限

    Returns:
        是否拥有权限
    """
    permissions = get_permissions_for_role(user_role)
    return required_permission in permissions


def has_any_permission(user_role: Role, required_permissions: List[Permission]) -> bool:
    """
    检查用户角色是否拥有任一指定权限

    Args:
        user_role: 用户角色
        required_permissions: 需要的权限列表

    Returns:
        是否拥有任一权限
    """
    permissions = get_permissions_for_role(user_role)
    return any(perm in permissions for perm in required_permissions)


def has_all_permissions(user_role: Role, required_permissions: List[Permission]) -> bool:
    """
    检查用户角色是否拥有所有指定权限

    Args:
        user_role: 用户角色
        required_permissions: 需要的权限列表

    Returns:
        是否拥有所有权限
    """
    permissions = get_permissions_for_role(user_role)
    return all(perm in permissions for perm in required_permissions)
