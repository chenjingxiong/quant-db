# -*- coding: utf-8 -*-
"""
认证服务模块

提供用户认证、授权、JWT Token管理等功能
"""
from .auth_service import AuthService, get_auth_service
from .jwt_handler import JWTHandler, get_jwt_handler
from .password_handler import PasswordHandler, get_password_handler
from .apikey_handler import APIKeyHandler, get_apikey_handler
from .audit_logger import AuditLogger, get_audit_logger
from .permissions import Permission, Role, get_permissions_for_role, has_permission

__all__ = [
    "AuthService",
    "get_auth_service",
    "JWTHandler",
    "get_jwt_handler",
    "PasswordHandler",
    "get_password_handler",
    "APIKeyHandler",
    "get_apikey_handler",
    "AuditLogger",
    "get_audit_logger",
    "Permission",
    "Role",
    "get_permissions_for_role",
    "has_permission",
]
