# -*- coding: utf-8 -*-
"""
消息发布者

提供消息发布功能
"""
import json
from typing import Any, Dict, Optional
from loguru import logger
import aio_pika

from .connection import RabbitMQConnection, get_rabbitmq_connection


class MessagePublisher:
    """消息发布者"""

    def __init__(self, connection: Optional[RabbitMQConnection] = None):
        """
        初始化消息发布者

        Args:
            connection: RabbitMQ连接，如果为None则使用全局实例
        """
        self.connection = connection
        self._channel: Optional[aio_pika.RobustChannel] = None

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
        return self._channel

    async def publish(
        self,
        exchange: str,
        routing_key: str,
        message: Dict[str, Any],
        persistent: bool = True,
    ) -> bool:
        """
        发布消息

        Args:
            exchange: 交换机名称
            routing_key: 路由键
            message: 消息内容
            persistent: 是否持久化

        Returns:
            是否发布成功
        """
        try:
            channel = await self._get_channel()

            # 序列化消息
            message_body = json.dumps(message).encode()

            # 创建消息
            message_obj = aio_pika.Message(
                message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT if persistent else aio_pika.DeliveryMode.NOT_PERSISTENT,
                content_type="application/json",
            )

            # 发布消息
            await channel.default_exchange.publish(
                message_obj,
                routing_key=routing_key,
            )

            logger.debug(f"Published message to {exchange}/{routing_key}: {message}")
            return True

        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False

    async def publish_quote(self, symbol: str, quote_data: Dict[str, Any]) -> bool:
        """
        发布行情消息

        Args:
            symbol: 股票代码
            quote_data: 行情数据

        Returns:
            是否发布成功
        """
        message = {
            "type": "quote",
            "symbol": symbol,
            "data": quote_data,
        }

        market = quote_data.get("market", "SH")
        routing_key = f"stock.{market.lower()}.{symbol}"

        return await self.publish("quotes", routing_key, message)

    async def publish_bar(
        self, symbol: str, interval: str, bar_data: Dict[str, Any]
    ) -> bool:
        """
        发布K线消息

        Args:
            symbol: 股票代码
            interval: 周期
            bar_data: K线数据

        Returns:
            是否发布成功
        """
        message = {
            "type": "bar",
            "symbol": symbol,
            "interval": interval,
            "data": bar_data,
        }

        routing_key = f"stock.bar.{symbol}.{interval}"

        return await self.publish("bars", routing_key, message)

    async def publish_alert(self, alert_type: str, alert_data: Dict[str, Any]) -> bool:
        """
        发布告警消息

        Args:
            alert_type: 告警类型
            alert_data: 告警数据

        Returns:
            是否发布成功
        """
        message = {
            "type": "alert",
            "alert_type": alert_type,
            "data": alert_data,
            "timestamp": alert_data.get("timestamp"),
        }

        return await self.publish("alerts", "", message)

    async def publish_event(
        self, event_type: str, event_data: Dict[str, Any]
    ) -> bool:
        """
        发布事件消息

        Args:
            event_type: 事件类型
            event_data: 事件数据

        Returns:
            是否发布成功
        """
        message = {
            "type": "event",
            "event_type": event_type,
            "data": event_data,
        }

        routing_key = f"event.{event_type}"

        return await self.publish("events", routing_key, message)

    async def batch_publish(
        self, messages: list[tuple[str, str, Dict[str, Any]]]
    ) -> int:
        """
        批量发布消息

        Args:
            messages: 消息列表，每个元素为 (exchange, routing_key, message) 元组

        Returns:
            成功发布的消息数量
        """
        success_count = 0

        for exchange, routing_key, message in messages:
            if await self.publish(exchange, routing_key, message):
                success_count += 1

        return success_count
