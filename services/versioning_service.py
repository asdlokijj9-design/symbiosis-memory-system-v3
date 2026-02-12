"""
版本控制服务 - 保留所有历史版本，支持回溯
"""

from typing import Optional, List
from datetime import datetime
import sqlite3
import json


class VersioningService:
    """版本控制服务"""
    
    def __init__(self, db_path: str = None):
        """初始化版本控制服务
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path or r"/Users/imac/.openclaw/workspace/symbiosis-memory-system/memory.db"
        self._initialized = False
    
    async def _ensure_tables(self) -> None:
        """确保表存在"""
        if self._initialized:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建版本历史表（如果不存在）
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
    
    async def create_version(
        self,
        entity_type: str,
        entity_id: str,
        data: dict
    ) -> dict:
        """创建新版本
        
        Args:
            entity_type: 实体类型 (session, memory, log)
            entity_id: 实体ID
            data: 版本数据
            
        Returns:
            版本信息
        """
        await self._ensure_tables()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取当前版本号
        cursor.execute('''
            SELECT MAX(version) FROM versions 
            WHERE entity_type = ? AND entity_id = ?
        ''', (entity_type, entity_id))
        
        result = cursor.fetchone()
        new_version = (result[0] or 0) + 1
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO versions (entity_type, entity_id, version, data, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (entity_type, entity_id, new_version, json.dumps(data), timestamp))
        
        conn.commit()
        conn.close()
        
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "version": new_version,
            "created_at": timestamp
        }
    
    async def get_version(
        self,
        entity_type: str,
        entity_id: str,
        version: int = None
    ) -> Optional[dict]:
        """获取特定版本
        
        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            version: 版本号，None获取最新版本
            
        Returns:
            版本数据
        """
        await self._ensure_tables()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if version is None:
            # 获取最新版本
            cursor.execute('''
                SELECT version, data, created_at FROM versions 
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY version DESC LIMIT 1
            ''', (entity_type, entity_id))
        else:
            cursor.execute('''
                SELECT version, data, created_at FROM versions 
                WHERE entity_type = ? AND entity_id = ? AND version = ?
            ''', (entity_type, entity_id, version))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "version": result[0],
                "data": json.loads(result[1]),
                "created_at": result[2]
            }
        
        return None
    
    async def get_version_history(
        self,
        entity_type: str,
        entity_id: str
    ) -> List[dict]:
        """获取版本历史
        
        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            
        Returns:
            版本历史列表
        """
        await self._ensure_tables()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT version, data, created_at FROM versions 
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY version ASC
        ''', (entity_type, entity_id))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "version": r[0],
                "data": json.loads(r[1]),
                "created_at": r[2]
            }
            for r in results
        ]
    
    async def compare_versions(
        self,
        entity_type: str,
        entity_id: str,
        version1: int,
        version2: int
    ) -> dict:
        """比较两个版本
        
        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            version1: 版本1
            version2: 版本2
            
        Returns:
            版本比较结果
        """
        v1 = await self.get_version(entity_type, entity_id, version1)
        v2 = await self.get_version(entity_type, entity_id, version2)
        
        return {
            "version1": v1,
            "version2": v2,
            "changes": []  # 可以实现详细的差异比较
        }
    
    async def revert_to_version(
        self,
        entity_type: str,
        entity_id: str,
        target_version: int
    ) -> dict:
        """回滚到指定版本
        
        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            target_version: 目标版本号
            
        Returns:
            回滚结果
        """
        target = await self.get_version(entity_type, entity_id, target_version)
        
        if target is None:
            return {
                "success": False,
                "error": f"Version {target_version} not found"
            }
        
        # 创建新版本（回滚）
        result = await self.create_version(
            entity_type,
            entity_id,
            {
                "reverted_from": target_version,
                **target["data"]
            }
        )
        
        return {
            "success": True,
            "reverted_to_version": target_version,
            "new_version": result["version"]
        }
    
    async def delete_old_versions(
        self,
        entity_type: str,
        entity_id: str,
        keep_count: int = 10
    ) -> dict:
        """删除旧版本（保留最近N个）
        
        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            keep_count: 保留版本数量
            
        Returns:
            删除结果
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取所有版本号
        cursor.execute('''
            SELECT version FROM versions 
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY version DESC
        ''', (entity_type, entity_id))
        
        versions = [r[0] for r in cursor.fetchall()]
        
        # 删除旧版本
        to_delete = versions[keep_count:]
        if to_delete:
            cursor.execute('''
                DELETE FROM versions 
                WHERE entity_type = ? AND entity_id = ? AND version <= ?
            ''', (entity_type, entity_id, to_delete[-1]))
            
            conn.commit()
        
        conn.close()
        
        return {
            "deleted": len(to_delete),
            "kept": min(len(versions), keep_count)
        }
