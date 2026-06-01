# -*- coding: utf-8 -*-
"""
消息消费者

提供消息消费功能
"""
import json
from typing import Callable, Optional, Dict, Any
from loguru import logger
import aio_pika
import asyncio

from .connection import RabbitMQConnection, RabbitMQConnection, get_rabbitmq_connection


class MessageConsumer:
    """消息消费者"""

    def __init__(
        self,
        queue_name: str,
        connection: Optional[RabbitMQConnection] = None,
        auto_ack: bool = False,
    ):
        """
        初始化消息消费者

        Args:
            queue_name: 队列名称
            connection: RabbitMQ连接
            auto_ack: 是否自动确认
        """
        self.queue_name = queue_name
        self.connection = connection
        self.auto_ack = auto_ack
        self._channel: Optional[aio_pika.RobustChannel] = None
        self._consumer_tag: Optional[str] = None
        self._callbacks: Dict[str, Callable] = {}
        self._is_consuming = False

    async def _get_connection(self) -> RabbitMQConnection:
        """获取RabbitMQ连接"""
        if self.connection is None:
            return await get_rabbitmq_connection()
        return self.connection

    async def _get_channel(self) -> aio_pika.RobustChannel:
        """获取或创建通道"""
        if self._channel is None or self._channel.is_closed:
            conn = await self._get_connection()
            self._channel = await conn.create_channel()
            # 设置QoS
            await self._channel.set_qos(prefetch_count=10)
        return self._channel

    def register_callback(self, message_type: str, callback: Callable) -> None:
        """
        注册消息处理回调函数

        Args:
            message_type: 消息类型
            callback: 处理函数，签名为 async def callback(message: Dict) -> None
        """
        self._callbacks[message_type] = callback
        logger.debug(f"Registered callback for message type: {message_type}")

    async def start(self) -> None:
        """开始消费消息"""
        if self._is_consuming:
            logger.warning(f"Consumer for queue {self.queue_name} is already running")
            return

        try:
            channel = await self._get_channel()

            # 获取队列
            queue = await channel.get_queue(self.queue_name)

            # 创建消费者
            self._consumer_tag = await queue.consume(
                self._process_message,
                auto_ack=self.auto_ack,
            )

            self._is_consuming = True
            logger.info(f"Started consuming from queue: {self.queue_name}")

        except Exception as e:
            logger.error(f"Error starting consumer for queue {self.queue_name}: {e}")
            raise

    async def stop(self) -> None:
        """停止消费消息"""
        if not self._is_consuming:
            return

        try:
            if self._channel and self._consumer_tag:
                await self._channel.basic_cancel(self._consumer_tag)

            self._is_consuming = False
            logger.info(f"Stopped consuming from queue: {self.queue_name}")

        except Exception as e:
            logger.error(f"Error stopping consumer: {e}")

    async def _process_message(self, message: aio_pika.IncomingMessage) -> None:
        """
        处理接收到的消息

        Args:
            message: 消息对象
        """
        try:
            # 解析消息
            body = message.body.decode()
            data = json.loads(body)

            logger.debug(
                f"Received message from queue {self.queue_name}: {data}"
            )

            # 获取消息类型
            message_type = data.get("type", "default")

            # 查找对应的回调函数
            callback = self._callbacks.get(message_type)

            if callback:
                try:
                    # 调用回调函数
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)

                    # 手动确认消息
                    if not self.auto_ack:
                        await message.ack()

                except Exception as e:
                    logger.error(f"Error in callback for message type {message_type}: {e}")
                    # 拒绝消息并重新入队
                    if not self.auto_ack:
                        await message.reject(requeue=True)
            else:
                logger.warning(f"No callback registered for message type: {message_type}")
                # 确认消息（因为没有处理器）
                if not self.auto_ack:
                    await message.ack()

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing message JSON: {e}")
            if not self.auto_ack:
                await message.reject(requeue=False)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            if not self.auto_ack:
                await message.reject(requeue=True)

    async def __aenter__(self):
        """支持异步上下文管理器"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """支持异步上下文管理器"""
        await self.stop()


# ===========================
# 预定义消费者
# ===========================

class QuoteConsumer(MessageConsumer):
    """行情消息消费者"""

    def __init__(self, connection: Optional[RabbitMQConnection] = None):
        super().__init__("quote.processor", connection)

    async def on_quote(self, callback: Callable) -> None:
        """注册行情处理回调"""
        self.register_callback("quote", callback)


class IndicatorConsumer(MessageConsumer):
    """指标计算消费者"""

    def __init__(self, connection: Optional[RabbitMQConnection] = None):
        super().__init__("indicator.calculator", connection)

    async def on_bar(self, callback: Callable) -> None:
        """注册K线处理回调"""
        self.register_callback("bar", callback)


class AlertConsumer(MessageConsumer):
    """告警消息消费者"""

    def __init__(self, connection: Optional[RabbitMQConnection] = None):
        super().__init__("alert.monitor", connection)

    async def on_alert(self, callback: Callable) -> None:
        """注册告警处理回调"""
        self.register_callback("alert", callback)
