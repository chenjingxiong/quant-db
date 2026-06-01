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


def _get_ws_manager():
    """Lazy import to avoid circular dependency with api module"""
    from ..api.websocket import manager
    return manager


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    STOPPED = "stopped"
    PAUSED = "paused"


class CollectionTask:
    """采集任务"""

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
        self.task_id = task_id
        self.name = name
        self.adapter = adapter
        self.data_type = data_type
        self.symbols = symbols
        self.interval = interval
        self.cron = cron
        self.enabled = enabled
        self.priority = priority

        self.status = TaskStatus.PENDING
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.retry_count = 0

        self.total_runs = 0
        self.success_count = 0
        self.failed_count = 0
        self.total_collected = 0

        self.on_data_callback: Optional[Callable] = None

    def to_dict(self) -> dict:
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
    """数据采集调度器"""

    def __init__(self, config: Optional[Dict] = None):
        self.settings = get_settings()
        self.tasks: Dict[str, CollectionTask] = {}
        self._task_lock = asyncio.Lock()
        cache_size = getattr(self.settings, 'cache_size', 10000)
        self.data_cache = PriorityDataCache(max_size=cache_size)
        self.is_running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self.start_time: Optional[datetime] = None
        self.total_processed = 0

    def register_task(self, task: CollectionTask) -> bool:
        if task.task_id in self.tasks:
            logger.warning(f"Task {task.task_id} already exists")
            return False
        self.tasks[task.task_id] = task
        logger.info(f"Registered task: {task.name} ({task.task_id})")
        return True

    def unregister_task(self, task_id: str) -> bool:
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

    async def start(self):
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        self.is_running = True
        self.start_time = datetime.now()
        self._scheduler_task = asyncio.create_task(self._schedule_loop())
        logger.info("Collector scheduler started")

    async def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Collector scheduler stopped")

    async def _schedule_loop(self):
        logger.info("Schedule loop started")
        while self.is_running:
            try:
                now = datetime.now()
                for task in self.tasks.values():
                    if not task.enabled:
                        continue
                    should_run = False
                    if task.status == TaskStatus.PENDING:
                        should_run = True
                    elif task.next_run and task.next_run <= now:
                        should_run = True
                    if should_run:
                        asyncio.create_task(self._execute_task(task))
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Schedule loop error: {e}")
                await asyncio.sleep(5)
        logger.info("Schedule loop stopped")

    async def _execute_task(self, task: CollectionTask):
        if task.status == TaskStatus.RUNNING:
            return
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        try:
            logger.info(f"Executing task: {task.name} ({task.task_id})")
            if task.data_type == "stock":
                await self._collect_stock_quotes(task)
            elif task.data_type == "futures":
                await self._collect_futures_quotes(task)
            elif task.data_type == "index":
                await self._collect_index_quotes(task)
            else:
                logger.warning(f"Unknown data type: {task.data_type}")
            task.status = TaskStatus.SUCCESS
            task.success_count += 1
            task.error_message = None
            task.retry_count = 0
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
        ws = _get_ws_manager()
        for quote in quotes:
            data = {"type": "stock_quote", "data": quote, "ts": datetime.now()}
            await self.data_cache.put(data, priority=task.priority)
            symbol = quote.symbol if hasattr(quote, 'symbol') else quote.get("symbol", "")
            if symbol:
                try:
                    await ws.broadcast(
                        {"type": "quote", "data": quote.model_dump() if hasattr(quote, 'model_dump') else str(quote)},
                        f"stock:quotes:{symbol}"
                    )
                except Exception as e:
                    logger.debug(f"WS broadcast failed: {e}")
        try:
            await ws.broadcast({
                "type": "quotes_update",
                "data_type": "stock",
                "count": len(quotes),
                "timestamp": datetime.now().isoformat()
            }, "stock:quotes")
        except Exception as e:
            logger.debug(f"WS summary broadcast failed: {e}")
        logger.info(f"Collected {len(quotes)} stock quotes for task {task.task_id}")

    async def _collect_futures_quotes(self, task: CollectionTask):
        """采集期货行情"""
        quotes = await task.adapter.get_futures_quotes(task.symbols)
        task.total_collected += len(quotes)
        ws = _get_ws_manager()
        for quote in quotes:
            data = {"type": "futures_quote", "data": quote, "ts": datetime.now()}
            await self.data_cache.put(data, priority=task.priority)
            symbol = quote.symbol if hasattr(quote, 'symbol') else quote.get("symbol", "")
            if symbol:
                try:
                    await ws.broadcast(
                        {"type": "quote", "data": quote.model_dump() if hasattr(quote, 'model_dump') else str(quote)},
                        f"futures:quotes:{symbol}"
                    )
                except Exception as e:
                    logger.debug(f"WS broadcast failed: {e}")
        try:
            await ws.broadcast({
                "type": "quotes_update",
                "data_type": "futures",
                "count": len(quotes),
                "timestamp": datetime.now().isoformat()
            }, "futures:quotes")
        except Exception as e:
            logger.debug(f"WS summary broadcast failed: {e}")
        logger.info(f"Collected {len(quotes)} futures quotes for task {task.task_id}")

    async def _collect_index_quotes(self, task: CollectionTask):
        """采集指数行情"""
        quotes = await task.adapter.get_index_quotes(task.symbols)
        task.total_collected += len(quotes)
        ws = _get_ws_manager()
        for quote in quotes:
            data = {"type": "index_quote", "data": quote, "ts": datetime.now()}
            await self.data_cache.put(data, priority=task.priority)
            symbol = quote.symbol if hasattr(quote, 'symbol') else quote.get("symbol", "")
            if symbol:
                try:
                    await ws.broadcast(
                        {"type": "quote", "data": quote.model_dump() if hasattr(quote, 'model_dump') else str(quote)},
                        f"index:quotes:{symbol}"
                    )
                except Exception as e:
                    logger.debug(f"WS broadcast failed: {e}")
        try:
            await ws.broadcast({
                "type": "quotes_update",
                "data_type": "index",
                "count": len(quotes),
                "timestamp": datetime.now().isoformat()
            }, "index:quotes")
        except Exception as e:
            logger.debug(f"WS summary broadcast failed: {e}")
        logger.info(f"Collected {len(quotes)} index quotes for task {task.task_id}")

    def _calculate_next_run(self, task: CollectionTask) -> Optional[datetime]:
        if task.cron:
            return datetime.now() + timedelta(seconds=30)
        else:
            interval = getattr(self.settings, 'collect_interval', 5)
            return datetime.now() + timedelta(seconds=interval)

    async def get_cached_data(self, batch_size: int = 100) -> List[dict]:
        return await self.data_cache.get_batch(batch_size)

    def get_task_status(self, task_id: str) -> Optional[dict]:
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None

    def get_all_tasks(self) -> List[dict]:
        return [task.to_dict() for task in self.tasks.values()]

    def get_stats(self) -> dict:
        running_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)
        return {
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "total_tasks": len(self.tasks),
            "running_tasks": running_tasks,
            "enabled_tasks": sum(1 for t in self.tasks.values() if t.enabled),
            "cache_stats": self.data_cache.get_stats() if hasattr(self.data_cache, 'get_stats') else {},
        }

    async def pause_task(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        task.enabled = False
        task.status = TaskStatus.PAUSED
        logger.info(f"Paused task: {task_id}")
        return True

    async def resume_task(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        task.enabled = True
        task.status = TaskStatus.PENDING
        logger.info(f"Resumed task: {task_id}")
        return True
