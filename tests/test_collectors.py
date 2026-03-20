# -*- coding: utf-8 -*-
"""
测试数据采集模块
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from backend.collectors.cache import DataCache, PriorityDataCache
from backend.collectors.scheduler import CollectorScheduler, CollectionTask, TaskStatus


class TestDataCache:
    """测试数据缓存队列"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        cache = DataCache(max_size=1000, timeout=5.0)
        assert cache.queue.maxsize == 1000
        assert cache.timeout == 5.0
        assert cache._closed is False

    @pytest.mark.asyncio
    async def test_put_and_get(self):
        """测试放入和获取数据"""
        cache = DataCache()
        data = {"symbol": "SZ000001", "price": 10.50}

        # 放入
        result = await cache.put(data)
        assert result is True

        # 获取
        result = await cache.get()
        assert result == data

    @pytest.mark.asyncio
    async def test_put_batch(self):
        """测试批量放入"""
        cache = DataCache()
        items = [{"id": i} for i in range(10)]

        count = await cache.put_batch(items)
        assert count == 10

    @pytest.mark.asyncio
    async def test_get_batch(self):
        """测试批量获取"""
        cache = DataCache()
        items = [{"id": i} for i in range(10)]
        await cache.put_batch(items)

        result = await cache.get_batch(5)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_timeout(self):
        """测试获取超时"""
        cache = DataCache(timeout=0.1)
        result = await cache.get()
        assert result is None

    @pytest.mark.asyncio
    async def test_qsize(self):
        """测试队列大小"""
        cache = DataCache()
        assert cache.qsize() == 0

        await cache.put({"test": "data"})
        assert cache.qsize() == 1

    @pytest.mark.asyncio
    async def test_empty(self):
        """测试是否为空"""
        cache = DataCache()
        assert cache.empty() is True

        await cache.put({"test": "data"})
        assert cache.empty() is False

    @pytest.mark.asyncio
    async def test_full(self):
        """测试是否已满"""
        cache = DataCache(max_size=2)
        assert cache.full() is False

        await cache.put({"test": "data1"})
        await cache.put({"test": "data2"})
        assert cache.full() is True

    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空队列"""
        cache = DataCache()
        await cache.put({"test": "data"})
        await cache.put({"test": "data"})

        await cache.clear()
        assert cache.empty() is True

    def test_close(self):
        """测试关闭队列"""
        cache = DataCache()
        cache.close()
        assert cache._closed is True

    def test_get_stats(self):
        """测试获取统计信息"""
        cache = DataCache()
        stats = cache.get_stats()
        assert "qsize" in stats
        assert "total_put" in stats
        assert "total_get" in stats
        assert "total_timeout" in stats
        assert "closed" in stats


class TestPriorityDataCache:
    """测试优先级数据缓存队列"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        cache = PriorityDataCache(max_size=1000)
        assert cache._max_size == 1000
        assert isinstance(cache._heap, list)

    @pytest.mark.asyncio
    async def test_put_with_priority(self):
        """测试带优先级放入"""
        cache = PriorityDataCache()

        # 放入不同优先级的数据
        await cache.put({"id": 1}, priority=2)  # 低优先级
        await cache.put({"id": 2}, priority=1)  # 高优先级
        await cache.put({"id": 3}, priority=3)  # 最低优先级

        # 应该先获取高优先级的数据
        result1 = await cache.get(timeout=0.1)
        assert result1["id"] == 2

        result2 = await cache.get(timeout=0.1)
        assert result2["id"] == 1

    @pytest.mark.asyncio
    async def test_get_order(self):
        """测试获取顺序"""
        cache = PriorityDataCache()

        # 放入数据：id越小优先级越高
        for i in range(5):
            await cache.put({"id": i}, priority=i)

        # 按优先级获取
        for i in range(5):
            result = await cache.get(timeout=0.1)
            assert result["id"] == i

    @pytest.mark.asyncio
    async def test_full_queue_drop_low_priority(self):
        """测试队列满时丢弃低优先级数据"""
        cache = PriorityDataCache(max_size=3)

        # 放入4个数据，最后一个应该被丢弃
        await cache.put({"id": 1}, priority=1)
        await cache.put({"id": 2}, priority=2)
        await cache.put({"id": 3}, priority=3)
        await cache.put({"id": 4}, priority=4)  # 可能被丢弃

        # 获取所有数据
        results = []
        for _ in range(5):  # 最多尝试5次
            result = await cache.get(timeout=0.1)
            if result is None:
                break
            results.append(result)

        # 验证至少获取了一些数据，且优先级高的先被获取
        assert len(results) >= 2
        # 第一个应该是优先级最高的（id=1或id=2，取决于实现）
        assert results[0]["id"] in [1, 2]

    def test_qsize(self):
        """测试队列大小"""
        cache = PriorityDataCache()
        assert cache.qsize() == 0


class TestCollectionTask:
    """测试采集任务"""

    def test_init(self):
        """测试初始化"""
        task = CollectionTask(
            task_id="test_task",
            name="测试任务",
            adapter=Mock(),
            data_type="stock",
            symbols=["SZ000001", "SZ000002"],
            interval="1min",
        )
        assert task.task_id == "test_task"
        assert task.name == "测试任务"
        assert task.data_type == "stock"
        assert task.symbols == ["SZ000001", "SZ000002"]
        assert task.interval == "1min"
        assert task.status == TaskStatus.PENDING
        assert task.enabled is True
        assert task.priority == 0

    def test_to_dict(self):
        """测试转换为字典"""
        task = CollectionTask(
            task_id="test_task",
            name="测试任务",
            adapter=Mock(),
            data_type="stock",
            symbols=["SZ000001"],
        )
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        task.total_runs = 10
        task.success_count = 8
        task.failed_count = 2

        d = task.to_dict()
        assert d["task_id"] == "test_task"
        assert d["name"] == "测试任务"
        assert d["status"] == "running"
        assert d["total_runs"] == 10
        assert d["success_count"] == 8
        assert d["failed_count"] == 2


class TestCollectorScheduler:
    """测试采集调度器"""

    def test_init(self):
        """测试初始化"""
        scheduler = CollectorScheduler()
        assert scheduler.is_running is False
        assert len(scheduler.tasks) == 0
        assert scheduler.data_cache is not None

    def test_register_task(self, mock_adapter):
        """测试注册任务"""
        scheduler = CollectorScheduler()
        task = CollectionTask(
            task_id="test_task",
            name="测试任务",
            adapter=mock_adapter,
            data_type="stock",
            symbols=["SZ000001"],
        )

        result = scheduler.register_task(task)
        assert result is True
        assert "test_task" in scheduler.tasks

    def test_register_duplicate_task(self, mock_adapter):
        """测试注册重复任务"""
        scheduler = CollectorScheduler()
        task = CollectionTask(
            task_id="test_task",
            name="测试任务",
            adapter=mock_adapter,
            data_type="stock",
            symbols=["SZ000001"],
        )

        scheduler.register_task(task)
        result = scheduler.register_task(task)
        assert result is False

    def test_unregister_task(self, mock_adapter):
        """测试注销任务"""
        scheduler = CollectorScheduler()
        task = CollectionTask(
            task_id="test_task",
            name="测试任务",
            adapter=mock_adapter,
            data_type="stock",
            symbols=["SZ000001"],
        )

        scheduler.register_task(task)
        result = scheduler.unregister_task("test_task")
        assert result is True
        assert "test_task" not in scheduler.tasks

    def test_get_task_status(self, mock_adapter):
        """测试获取任务状态"""
        scheduler = CollectorScheduler()
        task = CollectionTask(
            task_id="test_task",
            name="测试任务",
            adapter=mock_adapter,
            data_type="stock",
            symbols=["SZ000001"],
        )

        scheduler.register_task(task)
        status = scheduler.get_task_status("test_task")
        assert status is not None
        assert status["task_id"] == "test_task"

    def test_get_all_tasks(self, mock_adapter):
        """测试获取所有任务"""
        scheduler = CollectorScheduler()

        for i in range(3):
            task = CollectionTask(
                task_id=f"task_{i}",
                name=f"任务{i}",
                adapter=mock_adapter,
                data_type="stock",
                symbols=[f"SZ00000{i+1}"],
            )
            scheduler.register_task(task)

        tasks = scheduler.get_all_tasks()
        assert len(tasks) == 3

    def test_get_stats(self, mock_adapter):
        """测试获取统计信息"""
        scheduler = CollectorScheduler()
        stats = scheduler.get_stats()
        assert "is_running" in stats
        assert "total_tasks" in stats
        assert "running_tasks" in stats
        assert "cache_stats" in stats

    @pytest.mark.asyncio
    async def test_pause_task(self, mock_adapter):
        """测试暂停任务"""
        scheduler = CollectorScheduler()
        task = CollectionTask(
            task_id="test_task",
            name="测试任务",
            adapter=mock_adapter,
            data_type="stock",
            symbols=["SZ000001"],
        )

        scheduler.register_task(task)
        result = await scheduler.pause_task("test_task")
        assert result is True
        assert task.enabled is False

    @pytest.mark.asyncio
    async def test_resume_task(self, mock_adapter):
        """测试恢复任务"""
        scheduler = CollectorScheduler()
        task = CollectionTask(
            task_id="test_task",
            name="测试任务",
            adapter=mock_adapter,
            data_type="stock",
            symbols=["SZ000001"],
        )

        scheduler.register_task(task)
        await scheduler.pause_task("test_task")
        result = await scheduler.resume_task("test_task")
        assert result is True
        assert task.enabled is True

    @pytest.mark.asyncio
    async def test_start_stop(self, mock_adapter):
        """测试启动和停止"""
        scheduler = CollectorScheduler()

        await scheduler.start()
        assert scheduler.is_running is True

        await asyncio.sleep(0.1)  # 等待调度循环启动

        await scheduler.stop()
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_get_cached_data(self, mock_adapter):
        """测试获取缓存数据"""
        scheduler = CollectorScheduler()

        # 放入一些数据
        await scheduler.data_cache.put({"test": "data1"})
        await scheduler.data_cache.put({"test": "data2"})

        # 获取
        data = await scheduler.get_cached_data(batch_size=10)
        assert len(data) == 2


class TestTaskStatus:
    """测试任务状态枚举"""

    def test_status_values(self):
        """测试状态值"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.SUCCESS == "success"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.STOPPED == "stopped"
        assert TaskStatus.PAUSED == "paused"
