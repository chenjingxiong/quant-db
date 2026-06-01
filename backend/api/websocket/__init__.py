# -*- coding: utf-8 -*-
"""
WebSocket连接管理
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
from loguru import logger
import json
import asyncio


class ConnectionManager:
    """
    WebSocket连接管理器

    管理所有WebSocket连接和消息订阅
    """

    def __init__(self):
        # 活跃连接
        self.active_connections: Dict[str, WebSocket] = {}

        # 订阅管理 {topic: set(connection_id)}
        self.subscriptions: Dict[str, Set[str]] = {}

        # 连接订阅 {connection_id: set(topics)}
        self.connection_subscriptions: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """接受新连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_subscriptions[client_id] = set()
        logger.info(f"WebSocket connected: {client_id}")

    def disconnect(self, client_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            # 清理订阅
            topics = self.connection_subscriptions.get(client_id, set())
            for topic in topics:
                if topic in self.subscriptions:
                    self.subscriptions[topic].discard(client_id)

            del self.active_connections[client_id]
            del self.connection_subscriptions[client_id]
            logger.info(f"WebSocket disconnected: {client_id}")

    async def subscribe(self, client_id: str, topic: str):
        """订阅主题"""
        if client_id not in self.active_connections:
            return False

        # 添加订阅
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(client_id)

        # 记录连接的订阅
        self.connection_subscriptions[client_id].add(topic)

        logger.info(f"Client {client_id} subscribed to {topic}")
        return True

    async def unsubscribe(self, client_id: str, topic: str):
        """取消订阅"""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)

        if client_id in self.connection_subscriptions:
            self.connection_subscriptions[client_id].discard(topic)

        logger.info(f"Client {client_id} unsubscribed from {topic}")

    async def send_personal_message(self, message: dict, client_id: str):
        """发送消息给指定客户端"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(f"Send message to {client_id} failed: {e}")
                self.disconnect(client_id)
                return False
        return False

    async def broadcast(self, message: dict, topic: str):
        """向订阅了指定主题的所有客户端广播消息"""
        if topic not in self.subscriptions:
            return

        failed_clients = []

        for client_id in self.subscriptions[topic]:
            success = await self.send_personal_message(message, client_id)
            if not success:
                failed_clients.append(client_id)

        # 清理失败的连接
        for client_id in failed_clients:
            self.disconnect(client_id)

    async def broadcast_to_all(self, message: dict):
        """向所有连接广播消息"""
        failed_clients = []

        for client_id in self.active_connections:
            success = await self.send_personal_message(message, client_id)
            if not success:
                failed_clients.append(client_id)

        for client_id in failed_clients:
            self.disconnect(client_id)

    def get_connection_count(self) -> int:
        """获取连接数"""
        return len(self.active_connections)

    def get_subscribers(self, topic: str) -> int:
        """获取主题订阅数"""
        return len(self.subscriptions.get(topic, set()))

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_connections": len(self.active_connections),
            "total_topics": len(self.subscriptions),
            "top_subscriptions": {
                topic: len(subs)
                for topic, subs in sorted(
                    self.subscriptions.items(),
                    key=lambda x: len(x[1]),
                    reverse=True
                )[:10]
            }
        }


# 全局连接管理器实例
manager = ConnectionManager()
