# -*- coding: utf-8 -*-
"""
API错误处理模块

提供统一的错误响应格式和异常处理
"""
from typing import Optional, Any, Dict
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
import traceback


class APIException(Exception):
    """API异常基类"""

    def __init__(
        self,
        message: str,
        code: str = "API_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthException(APIException):
    """认证异常"""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="AUTH_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class PermissionException(APIException):
    """权限异常"""

    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="PERMISSION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ValidationException(APIException):
    """数据验证异常"""

    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ResourceNotFoundException(APIException):
    """资源未找到异常"""

    def __init__(
        self,
        resource: str = "Resource",
        identifier: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"

        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class RateLimitException(APIException):
    """限流异常"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if retry_after is not None:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class DataException(APIException):
    """数据异常"""

    def __init__(
        self,
        message: str = "Data error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="DATA_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ExternalServiceException(APIException):
    """外部服务异常"""

    def __init__(
        self,
        service: str = "External service",
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if message is None:
            message = f"{service} unavailable"

        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service, **(details or {})},
        )


def create_error_response(
    message: str,
    code: str = "ERROR",
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """
    创建标准错误响应

    Args:
        message: 错误消息
        code: 错误代码
        status_code: HTTP状态码
        details: 额外详情

    Returns:
        JSONResponse
    """
    content = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        }
    }

    if details:
        content["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=content)


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """处理API异常"""
    logger.error(f"API Exception: {exc.code} - {exc.message}")

    return create_error_response(
        message=exc.message,
        code=exc.code,
        status_code=exc.status_code,
        details=exc.details if exc.details else None,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理HTTP异常"""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")

    return create_error_response(
        message=str(exc.detail),
        code="HTTP_ERROR",
        status_code=exc.status_code,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """处理请求验证异常"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(f"Validation Error: {errors}")

    return create_error_response(
        message="Request validation failed",
        code="VALIDATION_ERROR",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"errors": errors},
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理通用异常"""
    logger.error(f"Unhandled Exception: {type(exc).__name__} - {str(exc)}")
    logger.debug(traceback.format_exc())

    return create_error_response(
        message="Internal server error",
        code="INTERNAL_ERROR",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class ErrorResponse:
    """错误响应模型构建器"""

    @staticmethod
    def unauthorized(message: str = "Authentication required") -> Dict[str, Any]:
        """401 未授权响应"""
        return {
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": message,
            }
        }

    @staticmethod
    def forbidden(message: str = "Permission denied") -> Dict[str, Any]:
        """403 禁止访问响应"""
        return {
            "success": False,
            "error": {
                "code": "FORBIDDEN",
                "message": message,
            }
        }

    @staticmethod
    def not_found(resource: str = "Resource") -> Dict[str, Any]:
        """404 未找到响应"""
        return {
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": f"{resource} not found",
            }
        }

    @staticmethod
    def validation_error(errors: list) -> Dict[str, Any]:
        """422 验证错误响应"""
        return {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": errors}
            }
        }

    @staticmethod
    def rate_limit_exceeded(retry_after: int) -> Dict[str, Any]:
        """429 限流响应"""
        return {
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded",
                "details": {"retry_after": retry_after}
            }
        }

    @staticmethod
    def server_error(message: str = "Internal server error") -> Dict[str, Any]:
        """500 服务器错误响应"""
        return {
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": message,
            }
        }

    @staticmethod
    def service_unavailable(service: str = "Service") -> Dict[str, Any]:
        """503 服务不可用响应"""
        return {
            "success": False,
            "error": {
                "code": "SERVICE_UNAVAILABLE",
                "message": f"{service} temporarily unavailable",
            }
        }


class SuccessResponse:
    """成功响应模型构建器"""

    @staticmethod
    def created(data: Any = None, message: str = "Created successfully") -> Dict[str, Any]:
        """201 创建成功响应"""
        response = {
            "success": True,
            "message": message,
        }
        if data is not None:
            response["data"] = data
        return response

    @staticmethod
    def ok(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """200 成功响应"""
        response = {
            "success": True,
            "message": message,
        }
        if data is not None:
            response["data"] = data
        return response

    @staticmethod
    def accepted(data: Any = None, message: str = "Request accepted") -> Dict[str, Any]:
        """202 接受请求响应"""
        response = {
            "success": True,
            "message": message,
        }
        if data is not None:
            response["data"] = data
        return response

    @staticmethod
    def no_content() -> Dict[str, Any]:
        """204 无内容响应"""
        return {
            "success": True,
        }
