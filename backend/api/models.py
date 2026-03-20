# -*- coding: utf-8 -*-
"""
通用API响应模型

定义标准的请求和响应数据模型
"""
from typing import Optional, Any, List, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime


# 泛型类型变量
T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """标准API响应模型"""

    success: bool = Field(True, description="请求是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    error: Optional[dict] = Field(None, description="错误信息")


class PaginationParams(BaseModel):
    """分页参数"""

    page: int = Field(1, ge=1, description="页码（从1开始）")
    page_size: int = Field(20, ge=1, le=1000, description="每页数量")

    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""

    success: bool = Field(True, description="请求是否成功")
    data: List[T] = Field(default_factory=list, description="数据列表")
    pagination: dict = Field(
        default_factory=lambda: {
            "page": 1,
            "page_size": 20,
            "total": 0,
            "pages": 0,
        },
        description="分页信息",
    )
    message: Optional[str] = Field(None, description="响应消息")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="服务状态: healthy/degraded/unhealthy")
    timestamp: str = Field(..., description="检查时间")
    version: str = Field(..., description="服务版本")
    services: dict = Field(default_factory=dict, description="各服务状态")


class ErrorResponse(BaseModel):
    """错误响应模型"""

    success: bool = Field(False, description="请求是否成功")
    error: dict = Field(
        ...,
        description="错误详情",
        json_schema_extra={
            "example": {
                "code": "ERROR_CODE",
                "message": "Error message",
                "details": {},
            }
        },
    )


# ===========================
# 股票相关模型
# ===========================

class StockQuote(BaseModel):
    """股票行情"""

    symbol: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    price: float = Field(..., description="最新价")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    pre_close: float = Field(..., description="昨收价")
    volume: float = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")
    change: float = Field(..., description="涨跌额")
    change_percent: float = Field(..., description="涨跌幅(%)")
    timestamp: datetime = Field(..., description="时间戳")
    market: Optional[str] = Field(None, description="市场: SH/SZ")


class StockKLine(BaseModel):
    """股票K线"""

    symbol: str = Field(..., description="股票代码")
    interval: str = Field(..., description="K线周期: 1min/5min/15min/30min/60min/day/week/month")
    timestamp: datetime = Field(..., description="时间戳")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量")
    amount: Optional[float] = Field(None, description="成交额")


# ===========================
# 期货相关模型
# ===========================

class FuturesQuote(BaseModel):
    """期货行情"""

    symbol: str = Field(..., description="期货代码")
    name: Optional[str] = Field(None, description="期货名称")
    price: float = Field(..., description="最新价")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    pre_close: float = Field(..., description="昨结算价")
    volume: float = Field(..., description="成交量")
    open_interest: float = Field(..., description="持仓量")
    change: float = Field(..., description="涨跌额")
    change_percent: float = Field(..., description="涨跌幅(%)")
    timestamp: datetime = Field(..., description="时间戳")
    exchange: Optional[str] = Field(None, description="交易所")


# ===========================
# 指数相关模型
# ===========================

class IndexQuote(BaseModel):
    """指数行情"""

    symbol: str = Field(..., description="指数代码")
    name: Optional[str] = Field(None, description="指数名称")
    price: float = Field(..., description="最新点位")
    open: float = Field(..., description="开盘点位")
    high: float = Field(..., description="最高点位")
    low: float = Field(..., description="最低点位")
    pre_close: float = Field(..., description="昨收点位")
    volume: Optional[float] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    change: float = Field(..., description="涨跌点")
    change_percent: float = Field(..., description="涨跌幅(%)")
    timestamp: datetime = Field(..., description="时间戳")


# ===========================
# 数据采集相关模型
# ===========================

class CollectionTaskStatus(BaseModel):
    """采集任务状态"""

    task_id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    status: str = Field(..., description="状态: pending/running/success/failed/stopped/paused")
    enabled: bool = Field(..., description="是否启用")
    last_run: Optional[datetime] = Field(None, description="上次运行时间")
    next_run: Optional[datetime] = Field(None, description="下次运行时间")
    total_runs: int = Field(..., description="总运行次数")
    success_count: int = Field(..., description="成功次数")
    failed_count: int = Field(..., description="失败次数")
    total_collected: int = Field(..., description="总采集数量")
    error_message: Optional[str] = Field(None, description="错误消息")


class CollectionStats(BaseModel):
    """采集统计信息"""

    is_running: bool = Field(..., description="调度器是否运行")
    start_time: Optional[datetime] = Field(None, description="启动时间")
    total_tasks: int = Field(..., description="总任务数")
    running_tasks: int = Field(..., description="运行中任务数")
    enabled_tasks: int = Field(..., description="启用任务数")
    total_processed: int = Field(..., description="总处理数")
    cache_stats: dict = Field(default_factory=dict, description="缓存统计")


# ===========================
# 批量操作相关模型
# ===========================

class BatchRequest(BaseModel):
    """批量请求"""

    symbols: List[str] = Field(..., min_length=1, max_length=1000, description="股票代码列表")


class BatchResponse(BaseModel):
    """批量响应"""

    success: bool = Field(..., description="请求是否成功")
    total: int = Field(..., description="总数")
    successful: int = Field(..., description="成功数")
    failed: int = Field(..., description="失败数")
    data: List[Any] = Field(default_factory=list, description="成功数据")
    errors: List[dict] = Field(default_factory=list, description="失败详情")
    message: Optional[str] = Field(None, description="响应消息")


# ===========================
# 时间范围相关模型
# ===========================

class DateRange(BaseModel):
    """日期范围"""

    start: datetime = Field(..., description="开始时间")
    end: datetime = Field(..., description="结束时间")

    def to_tuple(self) -> tuple[datetime, datetime]:
        """转换为元组"""
        return (self.start, self.end)


# ===========================
# 排序相关模型
# ===========================

class SortParams(BaseModel):
    """排序参数"""

    field: str = Field("timestamp", description="排序字段")
    order: str = Field("desc", description="排序方向: asc/desc")

    @property
    def is_descending(self) -> bool:
        """是否降序"""
        return self.order.lower() == "desc"
