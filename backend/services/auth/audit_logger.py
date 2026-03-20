# -*- coding: utf-8 -*-
"""
审计日志模块

记录用户操作和系统事件
"""
from typing import Optional, Dict, Any
from loguru import logger
from datetime import datetime

from ...db import PostgresClient, get_postgres_client


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, postgres_client: Optional[PostgresClient] = None):
        """
        初始化审计日志记录器

        Args:
            postgres_client: PostgreSQL客户端
        """
        self.postgres_client = postgres_client

    async def _get_client(self) -> PostgresClient:
        """获取PostgreSQL客户端"""
        if self.postgres_client is None:
            return await get_postgres_client()
        return self.postgres_client

    async def log(
        self,
        user_id: Optional[int],
        action: str,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        记录审计日志

        Args:
            user_id: 用户ID
            action: 操作类型
            resource: 操作资源
            details: 详细信息
            ip_address: IP地址
            user_agent: 用户代理

        Returns:
            是否记录成功
        """
        try:
            client = await self._get_client()

            # 序列化详细信息
            import json
            details_json = json.dumps(details) if details else None

            # 插入审计日志
            await client.insert(
                "audit_logs",
                {
                    "user_id": user_id,
                    "action": action,
                    "resource": resource,
                    "details": details_json,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
            )

            return True

        except Exception as e:
            logger.error(f"Error writing audit log: {e}")
            return False

    async def log_auth(
        self,
        action: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
    ) -> bool:
        """
        记录认证相关日志

        Args:
            action: 操作类型 (login/logout/failed_login)
            user_id: 用户ID
            username: 用户名
            ip_address: IP地址
            user_agent: 用户代理
            success: 是否成功

        Returns:
            是否记录成功
        """
        details = {
            "username": username,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self.log(
            user_id=user_id,
            action=action,
            resource="auth",
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_api_access(
        self,
        user_id: Optional[int],
        method: str,
        path: str,
        status_code: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        记录API访问日志

        Args:
            user_id: 用户ID
            method: HTTP方法
            path: 请求路径
            status_code: 状态码
            ip_address: IP地址
            user_agent: 用户代理

        Returns:
            是否记录成功
        """
        details = {
            "method": method,
            "path": path,
            "status_code": status_code,
        }

        return await self.log(
            user_id=user_id,
            action="api_access",
            resource=path,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_data_access(
        self,
        user_id: Optional[int],
        action: str,
        data_type: str,
        symbols: Optional[list] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        记录数据访问日志

        Args:
            user_id: 用户ID
            action: 操作类型
            data_type: 数据类型
            symbols: 涉及的证券代码
            ip_address: IP地址

        Returns:
            是否记录成功
        """
        details = {
            "data_type": data_type,
            "symbols": symbols,
            "count": len(symbols) if symbols else 0,
        }

        return await self.log(
            user_id=user_id,
            action=action,
            resource="data",
            details=details,
            ip_address=ip_address,
        )

    async def log_system_event(
        self,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        记录系统事件日志

        Args:
            event_type: 事件类型
            details: 详细信息

        Returns:
            是否记录成功
        """
        return await self.log(
            user_id=None,
            action=event_type,
            resource="system",
            details=details,
        )

    async def get_user_logs(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        """
        获取用户审计日志

        Args:
            user_id: 用户ID
            limit: 返回数量
            offset: 偏移量

        Returns:
            审计日志列表
        """
        try:
            client = await self._get_client()

            query = """
                SELECT id, user_id, action, resource, details,
                       ip_address, user_agent, created_at
                FROM audit_logs
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """

            return await client.fetch_all(query, user_id, limit, offset)

        except Exception as e:
            logger.error(f"Error getting user logs: {e}")
            return []

    async def get_recent_logs(
        self,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """
        获取最近的审计日志

        Args:
            action: 操作类型过滤
            limit: 返回数量

        Returns:
            审计日志列表
        """
        try:
            client = await self._get_client()

            if action:
                query = """
                    SELECT id, user_id, action, resource, details,
                           ip_address, created_at
                    FROM audit_logs
                    WHERE action = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """
                return await client.fetch_all(query, action, limit)
            else:
                query = """
                    SELECT id, user_id, action, resource, details,
                           ip_address, created_at
                    FROM audit_logs
                    ORDER BY created_at DESC
                    LIMIT $1
                """
                return await client.fetch_all(query, limit)

        except Exception as e:
            logger.error(f"Error getting recent logs: {e}")
            return []


# 全局实例
_audit_logger: Optional[AuditLogger] = None


async def get_audit_logger() -> AuditLogger:
    """获取全局审计日志记录器实例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
