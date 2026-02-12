"""
持久化服务 - 确保每次对话后立即持久化
"""

from typing import Optional
from datetime import datetime
import asyncio
import sqlite3
import json


class PersistenceService:
    """持久化服务"""
    
    def __init__(self, db_path: str = None):
        """初始化持久化服务
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path or r"/Users/imac/.openclaw/workspace/symbiosis-memory-system/memory.db"
        self.pending_writes: list[dict] = []
        self.write_lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化数据库"""
        async with self.write_lock:
            if self._initialized:
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建所有表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT,
                    updated_at TEXT,
                    data BLOB
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    content TEXT,
                    priority INTEGER,
                    tags TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    category TEXT,
                    content TEXT,
                    timestamp TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT,
                    entity_id TEXT,
                    version INTEGER,
                    data BLOB,
                    created_at TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self._initialized = True
    
    async def save_session(self, session_id: str, data: dict) -> dict:
        """保存会话
        
        Args:
            session_id: 会话ID
            data: 会话数据
            
        Returns:
            保存结果
        """
        await self.initialize()
        
        async with self.write_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            # 检查是否存在
            cursor.execute('SELECT id FROM sessions WHERE id = ?', (session_id,))
            exists = cursor.fetchone()
            
            if exists:
                cursor.execute('''
                    UPDATE sessions 
                    SET updated_at = ?, data = ?
                    WHERE id = ?
                ''', (now, json.dumps(data), session_id))
            else:
                cursor.execute('''
                    INSERT INTO sessions (id, created_at, updated_at, data)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, now, now, json.dumps(data)))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "session_id": session_id,
                "saved_at": now
            }
    
    async def save_memory(
        self,
        category: str,
        content: str,
        priority: int = 5,
        tags: list = None
    ) -> dict:
        """保存记忆
        
        Args:
            category: 分类
            content: 内容
            priority: 优先级
            tags: 标签
            
        Returns:
            保存结果
        """
        await self.initialize()
        
        async with self.write_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO memory (category, content, priority, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (category, content, priority, json.dumps(tags or []), now, now))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "saved_at": now
            }
    
    async def save_daily_log(
        self,
        date: str,
        category: str,
        content: str
    ) -> dict:
        """保存每日日志
        
        Args:
            date: 日期
            category: 分类
            content: 内容
            
        Returns:
            保存结果
        """
        await self.initialize()
        
        async with self.write_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO daily_logs (date, category, content, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (date, category, content, timestamp))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "saved_at": timestamp
            }
    
    async def get_all_sessions(self, limit: int = None) -> list:
        """获取所有会话
        
        Args:
            limit: 可选，返回数量限制
            
        Returns:
            会话列表
        """
        await self.initialize()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if limit:
            cursor.execute('''
                SELECT id, created_at, updated_at, data FROM sessions ORDER BY updated_at DESC LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT id, created_at, updated_at, data FROM sessions ORDER BY updated_at DESC
            ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "created_at": row[1],
                "updated_at": row[2],
                "data": json.loads(row[3]) if row[3] else {}
            })
        
        conn.close()
        return results
    
    async def save_version(
        self,
        entity_type: str,
        entity_id: str,
        data: dict
    ) -> dict:
        """保存版本
        
        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            data: 数据
            
        Returns:
            保存结果
        """
        await self.initialize()
        
        async with self.write_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取当前版本号
            cursor.execute('''
                SELECT MAX(version) FROM versions 
                WHERE entity_type = ? AND entity_id = ?
            ''', (entity_type, entity_id))
            result = cursor.fetchone()
            new_version = (result[0] or 0) + 1
            
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO versions (entity_type, entity_id, version, data, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (entity_type, entity_id, new_version, json.dumps(data), now))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "version": new_version,
                "saved_at": now
            }
    
    async def close(self) -> None:
        """关闭服务"""
        async with self.write_lock:
            pass  # SQLite 无需显式关闭
    
    async def force_flush(self) -> dict:
        """强制刷新所有待处理的写入
        
        Returns:
            刷新结果
        """
        return {
            "flushed": len(self.pending_writes),
            "flushed_at": datetime.now().isoformat()
        }
