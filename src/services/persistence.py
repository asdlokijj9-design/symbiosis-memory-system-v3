"""
Persistence Service - 实时持久化服务
"""

import threading
import logging
import time
from datetime import datetime
from queue import Queue, Empty
from typing import Optional, Dict, Any, Callable

from .memory_db import MemoryDB

logger = logging.getLogger(__name__)


class PersistenceService:
    """
    实时持久化服务
    
    特点：
    - 内存缓存 + 定时刷盘（双保险）
    - 支持立即保存和队列保存
    - 自动崩溃恢复
    """
    
    def __init__(
        self,
        db: MemoryDB,
        flush_interval: float = 1.0,
        max_queue_size: int = 1000,
        auto_flush: bool = True
    ):
        """
        初始化持久化服务
        
        Args:
            db: MemoryDB 实例
            flush_interval: 自动刷盘间隔（秒）
            max_queue_size: 最大队列大小
            auto_flush: 是否自动刷盘
        """
        self.db = db
        self.flush_interval = flush_interval
        self.max_queue_size = max_queue_size
        self.auto_flush = auto_flush
        
        # 队列
        self._queue: Queue = Queue()
        
        # 状态
        self._running = False
        self._last_flush: Optional[datetime] = None
        self._flush_count = 0
        self._error_count = 0
        
        # 线程
        self._flush_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 统计
        self._total_saves = 0
        self._total_queues = 0
    
    def start(self) -> None:
        """启动持久化服务"""
        if self._running:
            return
        
        self._running = True
        
        if self.auto_flush:
            self._flush_thread = threading.Thread(target=self._auto_flush_loop, daemon=True)
            self._flush_thread.start()
        
        logger.info(f"持久化服务启动，flush_interval={self.flush_interval}s")
    
    def stop(self) -> None:
        """停止持久化服务（会强制刷盘）"""
        if not self._running:
            return
        
        self._running = False
        
        # 强制刷盘
        self.force_flush()
        
        if self._flush_thread:
            self._flush_thread.join(timeout=2)
        
        logger.info("持久化服务停止")
    
    def save_immediately(
        self,
        memory_type: str,
        content: Dict[str, Any],
        **kwargs
    ) -> int:
        """
        立即保存（绕过缓存）
        
        Args:
            memory_type: 记忆类型
            content: 内容
            **kwargs: 其他参数 (session_id, date, importance, tags)
        
        Returns:
            记忆ID
        """
        with self._lock:
            self._total_saves += 1
        
        try:
            memory_id = self.db.save_memory(
                memory_type=memory_type,
                content=content,
                **kwargs
            )
            
            self._last_flush = datetime.now()
            return memory_id
        
        except Exception as e:
            self._error_count += 1
            logger.error(f"立即保存失败: {e}")
            raise
    
    def queue_save(
        self,
        memory_type: str,
        content: Dict[str, Any],
        **kwargs
    ) -> bool:
        """
        加入保存队列（异步）
        
        Args:
            memory_type: 记忆类型
            content: 内容
            **kwargs: 其他参数
        
        Returns:
            是否成功加入队列
        """
        if self._queue.qsize() >= self.max_queue_size:
            logger.warning("队列已满，强制刷盘")
            self.force_flush()
        
        try:
            self._queue.put({
                'memory_type': memory_type,
                'content': content,
                'kwargs': kwargs,
                'timestamp': datetime.now()
            })
            
            self._total_queues += 1
            return True
        
        except Exception as e:
            self._error_count += 1
            logger.error(f"加入队列失败: {e}")
            return False
    
    def force_flush(self) -> int:
        """
        强制刷盘（清空缓存）
        
        Returns:
            刷新的条目数量
        """
        flushed = 0
        items = []
        
        # 取出所有队列项
        while True:
            try:
                item = self._queue.get_nowait()
                items.append(item)
            except Empty:
                break
        
        # 批量保存
        if items:
            try:
                for item in items:
                    self.db.save_memory(
                        memory_type=item['memory_type'],
                        content=item['content'],
                        **item.get('kwargs', {})
                    )
                    flushed += 1
                
                self._last_flush = datetime.now()
                self._flush_count += flushed
                logger.debug(f"刷盘完成: {flushed} 条")
            
            except Exception as e:
                self._error_count += 1
                logger.error(f"批量保存失败: {e}")
                # 重新加入队列
                for item in items:
                    self._queue.put(item)
        
        return flushed
    
    def get_queue_size(self) -> int:
        """获取队列中待保存的数量"""
        return self._queue.qsize()
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'running': self._running,
            'auto_flush': self.auto_flush,
            'flush_interval': self.flush_interval,
            'queue_size': self._queue.qsize(),
            'total_saves': self._total_saves,
            'total_queues': self._total_queues,
            'flush_count': self._flush_count,
            'error_count': self._error_count,
            'last_flush': self._last_flush.isoformat() if self._last_flush else None,
            'max_queue_size': self.max_queue_size
        }
    
    def _auto_flush_loop(self) -> None:
        """自动刷盘循环"""
        while self._running:
            try:
                time.sleep(self.flush_interval)
                
                if self._queue.qsize() > 0:
                    self.force_flush()
            
            except Exception as e:
                self._error_count += 1
                logger.error(f"自动刷盘错误: {e}")
    
    def wait_for_empty(self, timeout: float = 10.0) -> bool:
        """
        等待队列清空
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            是否在超时前清空
        """
        start = time.time()
        while time.time() - start < timeout:
            if self._queue.qsize() == 0:
                return True
            time.sleep(0.1)
        return False
    
    def set_flush_interval(self, interval: float) -> None:
        """
        设置自动刷盘间隔
        
        Args:
            interval: 间隔（秒）
        """
        self.flush_interval = max(0.1, interval)
        logger.info(f"刷盘间隔设置为: {interval}s")
