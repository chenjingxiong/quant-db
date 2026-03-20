# -*- coding: utf-8 -*-
"""
RabbitMQ连接管理

提供RabbitMQ连接的创建和管理
"""
import aio_pika
from typing import Optional
from loguru import logger


class RabbitMQConnection:
    """RabbitMQ连接管理类"""

    # 交换机定义
    EXCHANGES = {
        "quotes": {"type": "direct", "durable": True},
        "bars": {"type": "topic", "durable": True},
        "alerts": {"type": "fanout", "durable": True},
        "events": {"type": "topic", "durable": True},
    }

    # 队列定义
    QUEUES = {
        "quote.processor": {
            "exchange": "quotes",
            "routing_key": "stock",
            "durable": True,
        },
        "indicator.calculator": {
            "exchange": "bars",
            "routing_key": "stock.#",
            "durable": True,
        },
        "alert.monitor": {
            "exchange": "alerts",
            "routing_key": "#",
            "durable": True,
        },
        "data.processor": {
            "exchange": "events",
            "routing_key": "data.#",
            "durable": True,
        },
    }

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: str = "guest",
        password: str = "guest",
        virtual_host: str = "/",
        heartbeat: int = 60,
    ):
        """
        初始化RabbitMQ连接

        Args:
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码
            virtual_host: 虚拟主机
            heartbeat: 心跳间隔（秒）
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.heartbeat = heartbeat

        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.RobustChannel] = None

    async def connect(self) -> bool:
        """
        连接到RabbitMQ服务器

        Returns:
            是否连接成功
        """
        try:
            # 构建连接URL
            url = f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/{self.virtual_host}"

            # 创建连接
            self._connection = await aio_pika.connect_robust(
                url,
                heartbeat=self.heartbeat,
            )

            # 创建通道
            self._channel = await self._connection.channel()

            # 设置QoS（预取数量）
            await self._channel.set_qos(prefetch_count=10)

            # 声明交换机
            await self._declare_exchanges()

            # 声明队列
            await self._declare_queues()

            logger.info(
                f"Connected to RabbitMQ: {self.host}:{self.port}, vhost={self.virtual_host}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False

    async def disconnect(self) -> None:
        """断开RabbitMQ连接"""
        try:
            if self._channel:
                await self._channel.close()
            if self._connection:
                await self._connection.close()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")

    async def _declare_exchanges(self) -> None:
        """声明所有交换机"""
        for name, config in self.EXCHANGES.items():
            try:
                await self._channel.exchange_declare(
                    name=name,
                    type=config["type"],
                    durable=config.get("durable", True),
                )
                logger.debug(f"Declared exchange: {name}")
            except Exception as e:
                logger.error(f"Error declaring exchange {name}: {e}")

    async def _declare_queues(self) -> None:
        """声明所有队列并绑定"""
        for queue_name, config in self.QUEUES.items():
            try:
                # 声明队列
                await self._channel.queue_declare(
                    name=queue_name,
                    durable=config.get("durable", True),
                )

                # 绑定到交换机
                await self._channel.queue_bind(
                    queue=queue_name,
                    exchange=config["exchange"],
                    routing_key=config["routing_key"],
                )

                logger.debug(f"Declared and bound queue: {queue_name}")

            except Exception as e:
                logger.error(f"Error declaring queue {queue_name}: {e}")

    @property
    def connection(self) -> aio_pika.RobustConnection:
        """获取连接对象"""
        if self._connection is None:
            raise RuntimeError("RabbitMQ connection is not established. Call connect() first.")
        return self._connection

    @property
    def channel(self) -> aio_pika.RobustChannel:
        """获取通道对象"""
        if self._channel is None:
            raise RuntimeError("RabbitMQ channel is not established. Call connect() first.")
        return self._channel

    async def create_channel(self) -> aio_pika.RobustChannel:
        """
        创建新的通道

        Returns:
            新的通道对象
        """
        return await self.connection.channel()

    # ===========================
    # 健康检查
    # ===========================

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            RabbitMQ是否健康
        """
        try:
            if self._connection is None or self._connection.is_closed:
                return False
            return self._connection.is_open
        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {e}")
            return False


# ===========================
# 全局连接实例
# ===========================

_rabbitmq_connection: Optional[RabbitMQConnection] = None


async def get_rabbitmq_connection() -> RabbitMQConnection:
    """获取全局RabbitMQ连接实例"""
    global _rabbitmq_connection

    if _rabbitmq_connection is None:
        from ..config import get_settings

        settings = get_settings()
        _rabbitmq_connection = RabbitMQConnection(
            host=settings.rabbitmq_host,
            port=settings.rabbitmq_port,
            username=settings.rabbitmq_user,
            password=settings.rabbitmq_pass,
            virtual_host=settings.rabbitmq_vhost,
        )
        await _rabbitmq_connection.connect()

    return _rabbitmq_connection
