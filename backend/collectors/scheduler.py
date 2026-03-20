# -*- coding: utf-8 -*-
"""
数据采集调度器

管理多个数据采集任务，支持定时调度、失败重试、状态监控
"""
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from loguru import logger
from enum import Enum
import json

from ..config import get_settings
from ..adapters.base import BaseAdapter
from .cache import DataCache, PriorityDataCache
from ..api.websocket import manager


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"       # 待执行
    RUNNING = "running"       # 运行中
    SUCCESS = "success"       # 成功
    FAILED = "failed"         # 失败
    STOPPED = "stopped"       # 已停止
    PAUSED = "paused"         # 已暂停


class CollectionTask:
    """
    采集任务

    定义单个数据采集任务的配置和状态
    """

    def __init__(
        self,
        task_id: str,
        name: str,
        adapter: BaseAdapter,
        data_type: str,
        symbols: List[str],
        interval: str = "1min",
        cron: Optional[str] = None,
        enabled: bool = True,
        priority: int = 0,
    ):
        """
        初始化采集任务

        Args:
            task_id: 任务ID
            name: 任务名称
            adapter: 数据源适配器
            data_type: 数据类型 (stock/futures/index/sector)
            symbols: 采集标的列表
            interval: K线周期
            cron: Cron表达式
            enabled: 是否启用
            priority: 优先级
        """
        self.task_id = task_id
        self.name = name
        self.adapter = adapter
        self.data_type = data_type
        self.symbols = symbols
        self.interval = interval
        self.cron = cron
        self.enabled = enabled
        self.priority = priority

        # 状态
        self.status = TaskStatus.PENDING
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.retry_count = 0

        # 统计
        self.total_runs = 0
        self.success_count = 0
        self.failed_count = 0
        self.total_collected = 0

        # 回调
        self.on_data_callback: Optional[Callable] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "data_type": self.data_type,
            "symbols": self.symbols,
            "interval": self.interval,
            "status": self.status.value,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "error_message": self.error_message,
            "total_runs": self.total_runs,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "total_collected": self.total_collected,
        }


class CollectorScheduler:
    """
    数据采集调度器

    管理多个采集任务的调度执行
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化调度器

        Args:
            config: 配置字典
        """
        self.settings = get_settings()

        # 任务管理
        self.tasks: Dict[str, CollectionTask] = {}
        self._task_lock = asyncio.Lock()

        # 数据缓存
        cache_size = self.settings.cache_size
        self.data_cache = PriorityDataCache(max_size=cache_size)

        # 调度器状态
        self.is_running = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # 统计
        self.start_time: Optional[datetime] = None
        self.total_processed = 0

    def register_task(self, task: CollectionTask) -> bool:
        """
        注册采集任务

        Args:
            task: 采集任务

        Returns:
            bool: 是否成功
        """
        try:
            if task.task_id in self.tasks:
                logger.warning(f"Task {task.task_id} already exists")
                return False

            self.tasks[task.task_id] = task
            logger.info(f"Registered task: {task.name} ({task.task_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to register task: {e}")
            return False

    def unregister_task(self, task_id: str) -> bool:
        """
        注销采集任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功
        """
        try:
            if task_id not in self.tasks:
                logger.warning(f"Task {task_id} not found")
                return False

            task = self.tasks[task_id]
            if task.status == TaskStatus.RUNNING:
                logger.warning(f"Cannot unregister running task {task_id}")
                return False

            del self.tasks[task_id]
            logger.info(f"Unregistered task: {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister task: {e}")
            return False

    async def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.is_running = True
        self.start_time = datetime.now()

        # 启动调度循环
        self._scheduler_task = asyncio.create_task(self._schedule_loop())

        logger.info("Collector scheduler started")

    async def stop(self):
        """停止调度器"""
        if not self.is_running:
            return

        self.is_running = False

        # 等待调度循环结束
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("Collector scheduler stopped")

    async def _schedule_loop(self):
        """调度循环"""
        logger.info("Schedule loop started")

        while self.is_running:
            try:
                now = datetime.now()

                # 检查所有任务
                for task in self.tasks.values():
                    if not task.enabled:
                        continue

                    # 检查是否需要执行
                    should_run = False

                    if task.status == TaskStatus.PENDING:
                        should_run = True
                    elif task.next_run and task.next_run <= now:
                        should_run = True

                    if should_run:
                        # 创建任务
                        asyncio.create_task(self._execute_task(task))

                # 等待一段时间再检查
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Schedule loop error: {e}")
                await asyncio.sleep(5)

        logger.info("Schedule loop stopped")

    async def _execute_task(self, task: CollectionTask):
        """执行采集任务"""
        if task.status == TaskStatus.RUNNING:
            return

        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()

        try:
            logger.info(f"Executing task: {task.name} ({task.task_id})")

            # 根据数据类型执行不同的采集
            if task.data_type == "stock":
                await self._collect_stock_quotes(task)
            elif task.data_type == "futures":
                await self._collect_futures_quotes(task)
            elif task.data_type == "index":
                await self._collect_index_quotes(task)
            else:
                logger.warning(f"Unknown data type: {task.data_type}")

            # 更新状态
            task.status = TaskStatus.SUCCESS
            task.success_count += 1
            task.error_message = None
            task.retry_count = 0

            # 计算下次运行时间
            task.next_run = self._calculate_next_run(task)

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            task.status = TaskStatus.FAILED
            task.failed_count += 1
            task.error_message = str(e)
            task.retry_count += 1

        finally:
            task.total_runs += 1

    async def _collect_stock_quotes(self, task: CollectionTask):
        """采集股票行情"""
        quotes = await task.adapter.get_stock_quotes(task.symbols)

        task.total_collected += len(quotes)

        # 放入缓存并广播
        for quote in quotes:
            data = {
                "type": "stock_quote",
                "data": quote,
                "ts": datetime.now(),
            }
            await self.data_cache.put(data, priority=task.priority)

            # 广播到WebSocket订阅者
            symbol = quote.get("symbol", "")
            if symbol:
                await manager.broadcast(
                    {"type": "quote", "data": quote, "topic": f"stock:{symbol}"},
                    f"stock:quotes:{symbol}"
                )

        # 广播汇总
        await manager.broadcast({
            "type": "quotes_update",
            "data_type": "stock",
            "count": len(quotes),
            "timestamp": datetime.now().isoformat()
        }, "stock:quotes")

        logger.info(f"Collected {len(quotes)} stock quotes for task {task.task_id}")

    async def _collect_futures_quotes(self, task: CollectionTask):
        """采集期货行情"""
        quotes = await task.adapter.get_futures_quotes(task.symbols)

        task.total_collected += len(quotes)

        for quote in quotes:
            data = {
                "type": "futures_quote",
                "data": quote,
                "ts": datetime.now(),
            }
            await self.data_cache.put(data, priority=task.priority)

            # 广播到WebSocket订阅者
            symbol = quote.get("symbol", "")
            if symbol:
                await manager.broadcast(
                    {"type": "quote", "data": quote, "topic": f"futures:{symbol}"},
                    f"futures:quotes:{symbol}"
                )

        # 广播汇总
        await manager.broadcast({
            "type": "quotes_update",
            "data_type": "futures",
            "count": len(quotes),
            "timestamp": datetime.now().isoformat()
        }, "futures:quotes")

        logger.info(f"Collected {len(quotes)} futures quotes for task {task.task_id}")

    async def _collect_index_quotes(self, task: CollectionTask):
        """采集指数行情"""
        quotes = await task.adapter.get_index_quotes(task.symbols)

        task.total_collected += len(quotes)

        for quote in quotes:
            data = {
                "type": "index_quote",
                "data": quote,
                "ts": datetime.now(),
            }
            await self.data_cache.put(data, priority=task.priority)

            # 广播到WebSocket订阅者
            symbol = quote.get("symbol", "")
            if symbol:
                await manager.broadcast(
                    {"type": "quote", "data": quote, "topic": f"index:{symbol}"},
                    f"index:quotes:{symbol}"
                )

        # 广播汇总
        await manager.broadcast({
            "type": "quotes_update",
            "data_type": "index",
            "count": len(quotes),
            "timestamp": datetime.now().isoformat()
        }, "index:quotes")

        logger.info(f"Collected {len(quotes)} index quotes for task {task.task_id}")

    def _calculate_next_run(self, task: CollectionTask) -> Optional[datetime]:
        """计算下次运行时间"""
        if task.cron:
            # 解析cron表达式（简化版）
            # 实际使用时应该使用croniter库
            return datetime.now() + timedelta(seconds=30)
        else:
            # 默认间隔
            return datetime.now() + timedelta(seconds=self.settings.collect_interval)

    async def get_cached_data(self, batch_size: int = 100) -> List[dict]:
        """
        获取缓存数据

        Args:
            batch_size: 批量大小

        Returns:
            数据列表
        """
        return await self.data_cache.get_batch(batch_size)

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态字典
        """
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None

    def get_all_tasks(self) -> List[dict]:
        """获取所有任务"""
        return [task.to_dict() for task in self.tasks.values()]

    def get_stats(self) -> dict:
        """获取调度器统计信息"""
        running_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)

        return {
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "total_tasks": len(self.tasks),
            "running_tasks": running_tasks,
            "enabled_tasks": sum(1 for t in self.tasks.values() if t.enabled),
            "cache_stats": self.data_cache.get_stats(),
        }

    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.enabled = False
        task.status = TaskStatus.PAUSED
        logger.info(f"Paused task: {task_id}")
        return True

    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.enabled = True
        task.status = TaskStatus.PENDING
        logger.info(f"Resumed task: {task_id}")
        return True
