# -*- coding: utf-8 -*-
"""
WebSocket实时数据推送路由
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Set
from loguru import logger
import json
import uuid

from ..websocket import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str = Query(None, description="客户端ID"),
):
    """
    WebSocket连接端点

    消息格式:
    - 订阅: {"action": "subscribe", "topic": "stock:quotes:000001"}
    - 取消订阅: {"action": "unsubscribe", "topic": "stock:quotes:000001"}
    - 心跳: {"action": "ping"}
    """
    # 生成客户端ID
    if not client_id:
        client_id = str(uuid.uuid4())

    try:
        # 接受连接
        await manager.connect(websocket, client_id)

        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "WebSocket连接成功"
        })

        # 消息处理循环
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)

                action = message.get("action")
                topic = message.get("topic")

                if action == "subscribe" and topic:
                    # 订阅主题
                    await manager.subscribe(client_id, topic)
                    await websocket.send_json({
                        "type": "subscribed",
                        "topic": topic,
                        "message": f"已订阅: {topic}"
                    })

                elif action == "unsubscribe" and topic:
                    # 取消订阅
                    await manager.unsubscribe(client_id, topic)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "topic": topic,
                        "message": f"已取消订阅: {topic}"
                    })

                elif action == "ping":
                    # 心跳响应
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"未知操作: {action}"
                    })

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "JSON格式错误"
                })
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(client_id)


@router.get("/ws/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计"""
    return manager.get_stats()
