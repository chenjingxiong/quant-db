# -*- coding: utf-8 -*-
"""
认证API路由

提供用户注册、登录、令牌刷新、API Key管理等功能
"""
import time
from fastapi import APIRouter, HTTPException, status, Depends, Request, Body
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from loguru import logger

from ...middleware import require_auth, require_admin, get_rate_limit_key, check_rate_limit
from ...services.auth import (
    PasswordHandler,
    get_password_handler,
    JWTHandler,
    get_jwt_handler,
    APIKeyHandler,
    get_apikey_handler,
)
from ...services.auth.permissions import Role, Permission


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ===========================
# 请求/响应模型
# ===========================

class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    role: Optional[str] = Field("user", description="角色（可选，默认为user）")


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


class APIKeyCreateRequest(BaseModel):
    """创建API Key请求"""
    name: str = Field(..., min_length=1, max_length=100, description="API Key名称")
    scopes: list[str] = Field(["read"], description="权限范围")


class APIKeyResponse(BaseModel):
    """API Key响应"""
    api_key: str
    key_id: str
    name: str
    scopes: list[str]
    created_at: str


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    user_id: int
    username: str
    email: str
    role: str
    created_at: str
    last_login_at: Optional[str]


class PasswordChangeRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ===========================
# 辅助函数
# ===========================

def get_password_handler_instance():
    """获取密码处理器实例"""
    return get_password_handler()


def get_jwt_handler_instance():
    """获取JWT处理器实例"""
    return get_jwt_handler()


# ===========================
# 认证端点
# ===========================

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegisterRequest,
    request: Request,
    password_handler: PasswordHandler = Depends(get_password_handler_instance),
):
    """
    用户注册

    - 验证密码强度
    - 创建用户记录
    - 返回成功消息
    """
    # 限流检查
    rate_limit_key = get_rate_limit_key(request)
    await check_rate_limit(request, rate_limit_key, 3, 3600)  # 3次/小时

    # 验证密码强度
    is_valid, errors = password_handler.validate_strength(body.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Weak password", "messages": errors}
        )

    # TODO: 实际实现需要查询数据库
    # 这里只是模拟返回成功
    logger.info(f"User registration attempted: {body.username}")

    return {
        "message": "User registered successfully",
        "username": body.username,
        "email": body.email,
        "role": body.role
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLoginRequest,
    request: Request,
    password_handler: PasswordHandler = Depends(get_password_handler_instance),
    jwt_handler: JWTHandler = Depends(get_jwt_handler_instance),
):
    """
    用户登录

    - 验证用户名和密码
    - 生成访问令牌和刷新令牌
    - 返回令牌和用户信息
    """
    # 限流检查
    rate_limit_key = get_rate_limit_key(request)
    await check_rate_limit(request, rate_limit_key, 5, 60)  # 5次/分钟

    # TODO: 实际实现需要查询数据库验证用户
    # 这里模拟返回成功
    logger.info(f"User login attempted: {body.username}")

    # 模拟用户信息
    user = {
        "sub": "1",  # 用户ID
        "username": body.username,
        "email": f"{body.username}@example.com",
        "role": "admin",
    }

    # 创建令牌
    access_token = jwt_handler.create_access_token(user)
    refresh_token = jwt_handler.create_refresh_token(user)

    # 提取过期时间
    from datetime import datetime, timedelta, timezone
    expires_in = 30 * 60  # 30分钟

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=user
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    jwt_handler: JWTHandler = Depends(get_jwt_handler_instance),
):
    """
    刷新访问令牌

    - 验证刷新令牌
    - 生成新的访问令牌
    - 返回新的令牌对
    """
    payload = jwt_handler.verify_refresh_token(request.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # 创建新的访问令牌
    access_token = jwt_handler.create_access_token(payload)
    new_refresh_token = jwt_handler.create_refresh_token(payload)

    from datetime import datetime, timedelta, timezone
    expires_in = 30 * 60  # 30分钟

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=payload
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user(
    current_user: dict = Depends(require_auth),
):
    """
    获取当前用户信息

    需要认证
    """
    # TODO: 从数据库获取完整用户信息
    from datetime import datetime
    iat = current_user.get("iat", 0)
    last_login = datetime.fromtimestamp(iat).isoformat() if isinstance(iat, (int, float)) else str(iat)
    return UserInfoResponse(
        user_id=int(current_user.get("sub", "0")),
        username=current_user.get("username", ""),
        email=current_user.get("email", ""),
        role=current_user.get("role", "user"),
        created_at="2024-01-01T00:00:00",
        last_login_at=last_login
    )


# ===========================
# API Key管理端点
# ===========================

@router.post("/apikey", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: Request,
    current_user: dict = Depends(require_auth),
    apikey_handler: APIKeyHandler = Depends(get_apikey_handler),
):
    """
    创建API Key

    需要认证
    """
    # 解析请求体
    raw = await request.json()
    name = raw.get("name", "default")
    scopes = raw.get("scopes", ["read"])

    # 生成API Key
    api_key, key_hash = apikey_handler.generate_api_key()
    key_prefix = apikey_handler.get_key_prefix(api_key)
    key_id = f"{key_prefix}_{current_user.get('sub')}_{int(time.time())}"

    # TODO: 保存到数据库
    logger.info(f"API Key created for user {current_user.get('username')}: {key_id}")

    from datetime import datetime
    return APIKeyResponse(
        api_key=api_key,
        key_id=key_id,
        name=name,
        scopes=scopes,
        created_at=datetime.now().isoformat()
    )


@router.delete("/apikey/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: dict = Depends(require_auth),
):
    """
    删除API Key

    需要认证
    """
    # TODO: 从数据库删除API Key
    logger.info(f"API Key deletion attempted: {key_id}")

    return {
        "message": "API Key deleted successfully"
    }


@router.get("/apikey", response_model=list)
async def list_api_keys(
    current_user: dict = Depends(require_auth),
):
    """
    列出用户的API Keys

    需要认证
    """
    # TODO: 从数据库查询用户的API Keys
    return [
        {
            "key_id": f"key_{current_user.get('sub')}_1",
            "name": "Production Key",
            "scopes": ["read", "write"],
            "created_at": "2024-01-01T00:00:00",
            "last_used_at": "2024-01-01T12:00:00"
        }
    ]


# ===========================
# 密码管理端点
# ===========================

@router.post("/password/change")
async def change_password(
    request: Request,
    current_user: dict = Depends(require_auth),
    password_handler: PasswordHandler = Depends(get_password_handler_instance),
):
    """
    修改密码

    需要认证
    """
    # 解析请求体
    raw = await request.json()
    old_password = raw.get("old_password", "")
    new_password = raw.get("new_password", "")

    if not old_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="old_password and new_password are required"
        )

    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters"
        )

    # TODO: 验证旧密码
    # TODO: 更新数据库中的密码

    logger.info(f"Password change attempted for user {current_user.get('username')}")

    return {
        "message": "Password changed successfully"
    }


@router.post("/password/reset")
async def reset_password(
    email: EmailStr,
):
    """
    重置密码（通过邮件）

    - 生成重置令牌
    - 发送邮件
    """
    # 限流检查
    # 注意：这里使用email作为限流键
    # TODO: 实现邮件发送功能

    logger.info(f"Password reset requested for: {email}")

    return {
        "message": "If the email exists, a password reset link has been sent"
    }
