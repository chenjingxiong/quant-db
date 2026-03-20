# -*- coding: utf-8 -*-
"""
数据缓存队列
"""
import asyncio
from typing import Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger
import json


class DataCache:
    """
    数据缓存队列

    使用异步队列实现数据缓存，支持批量获取和超时处理
    """

    def __init__(self, max_size: int = 10000, timeout: float = 5.0):
        """
        初始化缓存队列

        Args:
            max_size: 队列最大大小
            timeout: 获取数据超时时间(秒)
        """
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.timeout = timeout
        self._closed = False

        # 统计信息
        self._total_put = 0
        self._total_get = 0
        self._total_timeout = 0

    async def put(self, item: Any, timeout: Optional[float] = None) -> bool:
        """
        放入数据

        Args:
            item: 数据项
            timeout: 超时时间

        Returns:
            bool: 是否成功
        """
        if self._closed:
            logger.warning("DataCache: queue is closed")
            return False

        try:
            timeout = timeout or self.timeout
            await asyncio.wait_for(self.queue.put(item), timeout=timeout)
            self._total_put += 1
            return True
        except asyncio.TimeoutError:
            logger.warning(f"DataCache: put timeout after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"DataCache: put error - {e}")
            return False

    async def get(self, timeout: Optional[float] = None) -> Any:
        """
        获取数据

        Args:
            timeout: 超时时间

        Returns:
            数据项，超时返回None
        """
        if self._closed and self.queue.empty():
            return None

        try:
            timeout = timeout or self.timeout
            item = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            self._total_get += 1
            return item
        except asyncio.TimeoutError:
            self._total_timeout += 1
            return None
        except Exception as e:
            logger.error(f"DataCache: get error - {e}")
            return None

    async def get_batch(self, batch_size: int, timeout: Optional[float] = None) -> List[Any]:
        """
        批量获取数据

        Args:
            batch_size: 批量大小
            timeout: 总超时时间

        Returns:
            数据列表
        """
        items = []
        deadline = datetime.now() + timedelta(seconds=timeout or self.timeout * batch_size)

        while len(items) < batch_size:
            remaining = (deadline - datetime.now()).total_seconds()
            if remaining <= 0:
                break

            item = await self.get(timeout=remaining)
            if item is None:
                break

            items.append(item)

        return items

    async def put_batch(self, items: List[Any], timeout: Optional[float] = None) -> int:
        """
        批量放入数据

        Args:
            items: 数据列表
            timeout: 单个项超时时间

        Returns:
            成功放入的数量
        """
        count = 0
        for item in items:
            if await self.put(item, timeout):
                count += 1
            else:
                break
        return count

    def qsize(self) -> int:
        """获取队列大小"""
        return self.queue.qsize()

    def empty(self) -> bool:
        """是否为空"""
        return self.queue.empty()

    def full(self) -> bool:
        """是否已满"""
        return self.queue.full()

    async def clear(self):
        """清空队列"""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def close(self):
        """关闭队列"""
        self._closed = True

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "qsize": self.qsize(),
            "total_put": self._total_put,
            "total_get": self._total_get,
            "total_timeout": self._total_timeout,
            "closed": self._closed,
        }


class PriorityDataCache(DataCache):
    """
    优先级数据缓存队列

    支持按优先级处理数据
    """

    def __init__(self, max_size: int = 10000, timeout: float = 5.0):
        super().__init__(max_size, timeout)
        # 使用优先级队列
        import heapq
        self._heap: list = []
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition()
        self._max_size = max_size

    async def put(self, item: Any, priority: int = 0, timeout: Optional[float] = None) -> bool:
        """
        放入数据（带优先级）

        Args:
            item: 数据项
            priority: 优先级（数字越小优先级越高）
            timeout: 超时时间

        Returns:
            bool: 是否成功
        """
        if self._closed:
            return False

        try:
            async with self._lock:
                if len(self._heap) >= self._max_size:
                    # 队列已满，移除最低优先级的项
                    self._heap.sort()
                    self._heap.pop()

                import heapq
                heapq.heappush(self._heap, (priority, datetime.now(), item))
                self._total_put += 1

            async with self._condition:
                self._condition.notify()

            return True

        except Exception as e:
            logger.error(f"PriorityDataCache: put error - {e}")
            return False

    async def get(self, timeout: Optional[float] = None) -> Any:
        """获取最高优先级的数据"""
        if self._closed and not self._heap:
            return None

        try:
            async with self._condition:
                await asyncio.wait_for(
                    self._condition.wait_for(lambda: len(self._heap) > 0 or self._closed),
                    timeout=timeout or self.timeout
                )

            async with self._lock:
                if not self._heap:
                    return None

                import heapq
                priority, ts, item = heapq.heappop(self._heap)
                self._total_get += 1
                return item

        except asyncio.TimeoutError:
            self._total_timeout += 1
            return None
        except Exception as e:
            logger.error(f"PriorityDataCache: get error - {e}")
            return None

    def qsize(self) -> int:
        """获取队列大小"""
        return len(self._heap)
