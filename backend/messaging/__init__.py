# -*- coding: utf-8 -*-
"""
消息队列模块

提供RabbitMQ消息队列的连接和操作接口
"""
from .connection import RabbitMQConnection, get_rabbitmq_connection
from .publisher import MessagePublisher
from .consumer import MessageConsumer

__all__ = [
    "RabbitMQConnection",
    "get_rabbitmq_connection",
    "MessagePublisher",
    "MessageConsumer",
]
