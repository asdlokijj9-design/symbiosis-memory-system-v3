"""
实时服务 - 处理实时记忆更新
"""

import asyncio
from typing import Optional, Callable
from datetime import datetime


class RealTimeService:
    """实时记忆更新服务"""
    
    def __init__(self, db_path: str = None):
        """初始化实时服务
        
        Args:
            db_path: 数据库路径
        """
        self.subscribers: list[Callable] = []
        self.buffer: list[dict] = []
        self.buffer_size = 100
        self.flush_interval = 1.0  # 秒
    
    async def register_subscriber(self, callback: Callable) -> None:
        """注册实时更新回调
        
        Args:
            callback: 回调函数
        """
        if callback not in self.subscribers:
            self.subscribers.append(callback)
    
    async def unregister_subscriber(self, callback: Callable) -> None:
        """取消注册回调
        
        Args:
            callback: 回调函数
        """
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    async def notify_subscribers(self, event: dict) -> None:
        """通知所有订阅者
        
        Args:
            event: 事件数据
        """
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception:
                pass  # 确保一个订阅者失败不影响其他订阅者
    
    async def buffer_update(self, update: dict) -> None:
        """缓冲更新
        
        Args:
            update: 更新数据
        """
        self.buffer.append({
            **update,
            "buffered_at": datetime.now().isoformat()
        })
        
        if len(self.buffer) >= self.buffer_size:
            await self.flush_buffer()
    
    async def flush_buffer(self) -> None:
        """刷新缓冲区"""
        if self.buffer:
            updates = self.buffer.copy()
            self.buffer.clear()
            await self.notify_subscribers({
                "type": "batch_update",
                "updates": updates,
                "flushed_at": datetime.now().isoformat()
            })
    
    async def close(self) -> None:
        """关闭服务"""
        await self.flush_buffer()
        self.subscribers.clear()
