# -*- coding: utf-8 -*-
"""
缓存预热模块

提供缓存预热、刷新和维护功能
"""
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from loguru import logger

from ..cache import get_cache_manager
from ..storage import TDEngineClient


class CacheWarmer:
    """缓存预热器"""

    def __init__(
        self,
        cache_manager=None,
        td_client: Optional[TDEngineClient] = None
    ):
        """
        初始化缓存预热器

        Args:
            cache_manager: 缓存管理器
            td_client: TDengine客户端
        """
        self.cache_manager = cache_manager
        self.td_client = td_client
        self._warm_tasks: List[Callable] = []

    def register_warm_task(self, task: Callable):
        """
        注册预热任务

        Args:
            task: 预热任务函数
        """
        self._warm_tasks.append(task)

    async def warm_all(self) -> Dict[str, Any]:
        """
        执行所有预热任务

        Returns:
            预热结果统计
        """
        results = {
            "success_count": 0,
            "failed_count": 0,
            "total_count": len(self._warm_tasks),
            "tasks": []
        }

        logger.info("开始缓存预热...")

        for task in self._warm_tasks:
            task_name = task.__name__
            start_time = datetime.now()

            try:
                await task()
                duration = (datetime.now() - start_time).total_seconds()
                results["tasks"].append({
                    "name": task_name,
                    "success": True,
                    "duration": duration
                })
                results["success_count"] += 1
                logger.info(f"预热任务 {task_name} 完成，耗时 {duration:.2f}秒")

            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                results["tasks"].append({
                    "name": task_name,
                    "success": False,
                    "error": str(e),
                    "duration": duration
                })
                results["failed_count"] += 1
                logger.error(f"预热任务 {task_name} 失败: {e}")

        logger.info(
            f"缓存预热完成: 成功 {results['success_count']}/{results['total_count']}"
        )

        return results

    async def warm_stock_list(self) -> int:
        """
        预热股票列表缓存

        Returns:
            预热的股票数量
        """
        if not self.td_client:
            logger.warning("TDengine客户端不可用，跳过股票列表预热")
            return 0

        try:
            # 获取所有股票列表
            query = "SELECT DISTINCT symbol FROM stock_quotes WHERE ts > NOW - 1d"
            result = await self.td_client.execute(query)

            if result and len(result) > 0:
                count = 0
                for row in result:
                    symbol = row.get("symbol")
                    if symbol:
                        # 缓存股票信息
                        await self.cache_manager.set(
                            f"stock:info:{symbol}",
                            {"symbol": symbol, "cached_at": datetime.now().isoformat()},
                            ttl=3600,
                            cache_type="stock_info"
                        )
                        count += 1

                logger.info(f"预热股票列表缓存: {count} 只股票")
                return count

        except Exception as e:
            logger.error(f"预热股票列表失败: {e}")

        return 0

    async def warm_hot_stocks(self, limit: int = 100) -> int:
        """
        预热热门股票缓存

        Args:
            limit: 预热的股票数量

        Returns:
            预热的股票数量
        """
        # 这里可以从数据库或配置获取热门股票列表
        hot_stocks = [
            "000001", "000002", "000003", "600000", "600036",
            "600519", "000858", "002594", "601318", "601988"
        ][:limit]

        count = 0
        for symbol in hot_stocks:
            try:
                # 预热股票行情
                await self.cache_manager.set(
                    f"stock:quote:{symbol}",
                    {"symbol": symbol, "price": 0, "cached": True},
                    ttl=60,
                    cache_type="stock_quote"
                )
                count += 1
            except Exception as e:
                logger.warning(f"预热股票 {symbol} 失败: {e}")

        logger.info(f"预热热门股票缓存: {count} 只")
        return count

    async def warm_index_list(self) -> int:
        """
        预热指数列表缓存

        Returns:
            预热的指数数量
        """
        major_indices = ["000001", "399001", "000300", "399006", "000905"]

        count = 0
        for index_code in major_indices:
            try:
                await self.cache_manager.set(
                    f"index:info:{index_code}",
                    {"symbol": index_code, "name": f"指数_{index_code}"},
                    ttl=3600,
                    cache_type="index_info"
                )
                count += 1
            except Exception as e:
                logger.warning(f"预热指数 {index_code} 失败: {e}")

        logger.info(f"预热指数列表缓存: {count} 个指数")
        return count

    async def warm_config_cache(self) -> int:
        """
        预热配置缓存

        Returns:
            缓存的配置数量
        """
        configs = {
            "api_rate_limit": {"default": "100/hour", "auth": "5/minute"},
            "features": {"websocket": True, "backtest": True},
            "maintenance": False,
        }

        count = 0
        for key, value in configs.items():
            try:
                await self.cache_manager.set(
                    f"config:{key}",
                    value,
                    ttl=7200,
                    cache_type="config"
                )
                count += 1
            except Exception as e:
                logger.warning(f"预热配置 {key} 失败: {e}")

        logger.info(f"预热配置缓存: {count} 个配置项")
        return count


class AsyncCacheWarmer(CacheWarmer):
    """异步缓存预热器（支持后台预热）"""

    def __init__(self, *args, refresh_interval: int = 300, **kwargs):
        """
        初始化异步缓存预热器

        Args:
            refresh_interval: 自动刷新间隔（秒）
        """
        super().__init__(*args, **kwargs)
        self.refresh_interval = refresh_interval
        self._is_running = False
        self._refresh_task: Optional[asyncio.Task] = None

    async def start_auto_refresh(self):
        """启动自动刷新"""
        if self._is_running:
            logger.warning("缓存预热器已在运行")
            return

        self._is_running = True
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        logger.info(f"缓存自动刷新已启动，间隔: {self.refresh_interval}秒")

    async def stop_auto_refresh(self):
        """停止自动刷新"""
        if not self._is_running:
            return

        self._is_running = False

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        logger.info("缓存自动刷新已停止")

    async def _refresh_loop(self):
        """刷新循环"""
        while self._is_running:
            try:
                await self.warm_all()
            except Exception as e:
                logger.error(f"缓存刷新失败: {e}")

            # 等待下次刷新
            await asyncio.sleep(self.refresh_interval)


# 全局实例
_cache_warmer: Optional[CacheWarmer] = None


def get_cache_warmer() -> CacheWarmer:
    """获取全局缓存预热器实例"""
    global _cache_warmer
    if _cache_warmer is None:
        _cache_warmer = CacheWarmer()
    return _cache_warmer
