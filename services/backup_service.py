"""
备份服务 - 本地副本自动备份
"""

import sqlite3
from datetime import datetime
from pathlib import Path
import json
import shutil
import asyncio
from typing import Optional


class BackupService:
    """本地备份服务"""
    
    def __init__(self, db_path: str = None, backup_dir: str = None):
        """初始化备份服务
        
        Args:
            db_path: 原始数据库路径
            backup_dir: 备份目录
        """
        self.db_path = db_path or ":memory:"
        self.backup_dir = Path(backup_dir) if backup_dir else \
            Path.home() / ".openclaw" / "workspace" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = 10
    
    async def create_backup(self) -> dict:
        """创建备份
        
        Returns:
            备份结果
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}.db"
        
        try:
            # 复制数据库文件
            if self.db_path != ":memory:":
                shutil.copy2(self.db_path, backup_path)
            else:
                # 内存数据库 - 导出为JSON
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 导出所有表
                tables = ['sessions', 'memory', 'daily_logs', 'versions']
                data = {}
                
                for table in tables:
                    cursor.execute(f"SELECT * FROM {table}")
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    data[table] = [dict(zip(columns, row)) for row in rows]
                
                conn.close()
                
                # 写入JSON文件
                async with aiofiles.open(backup_path.with_suffix('.json'), 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(data, indent=2, ensure_ascii=False))
                
                backup_path = backup_path.with_suffix('.json')
            
            # 清理旧备份
            await self._cleanup_old_backups()
            
            return {
                "success": True,
                "backup_path": str(backup_path),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _cleanup_old_backups(self) -> None:
        """清理旧备份"""
        backups = sorted(self.backup_dir.glob("backup_*"), key=lambda p: p.stat().st_mtime)
        
        while len(backups) > self.max_backups:
            old_backup = backups.pop(0)
            old_backup.unlink()
    
    async def restore_backup(self, backup_path: str = None) -> dict:
        """恢复备份
        
        Args:
            backup_path: 备份文件路径，None使用最新备份
            
        Returns:
            恢复结果
        """
        if backup_path is None:
            backups = sorted(self.backup_dir.glob("backup_*"), key=lambda p: p.stat().st_mtime)
            if not backups:
                return {
                    "success": False,
                    "error": "No backups found"
                }
            backup_path = str(backups[-1])
        
        try:
            backup_file = Path(backup_path)
            
            if backup_file.suffix == '.json':
                # 恢复JSON备份
                async with aiofiles.open(backup_file, 'r', encoding='utf-8') as f:
                    data = json.loads(await f.read())
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for table, rows in data.items():
                    for row in rows:
                        if table == 'sessions':
                            cursor.execute('''
                                INSERT OR REPLACE INTO sessions (id, created_at, updated_at, data)
                                VALUES (?, ?, ?, ?)
                            ''', (row['id'], row['created_at'], row['updated_at'], row['data']))
                        elif table == 'memory':
                            cursor.execute('''
                                INSERT INTO memory (category, content, priority, tags, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (row['category'], row['content'], row['priority'], 
                                  row['tags'], row['created_at'], row['updated_at']))
                        elif table == 'daily_logs':
                            cursor.execute('''
                                INSERT INTO daily_logs (date, category, content, timestamp)
                                VALUES (?, ?, ?, ?)
                            ''', (row['date'], row['category'], row['content'], row['timestamp']))
                        elif table == 'versions':
                            cursor.execute('''
                                INSERT INTO versions (entity_type, entity_id, version, data, created_at)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (row['entity_type'], row['entity_id'], row['version'],
                                  row['data'], row['created_at']))
                
                conn.commit()
                conn.close()
            
            else:
                # 恢复数据库文件备份
                shutil.copy2(backup_file, self.db_path)
            
            return {
                "success": True,
                "restored_from": backup_path,
                "restored_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_backups(self) -> list:
        """列出所有备份
        
        Returns:
            备份列表
        """
        backups = []
        
        for backup in sorted(self.backup_dir.glob("backup_*"), key=lambda p: p.stat().st_mtime):
            backups.append({
                "path": str(backup),
                "size": backup.stat().st_size,
                "created_at": datetime.fromtimestamp(backup.stat().st_mtime).isoformat()
            })
        
        return backups
    
    async def get_latest_backup(self) -> Optional[dict]:
        """获取最新备份
        
        Returns:
            最新备份信息
        """
        backups = await self.list_backups()
        
        if backups:
            return backups[-1]
        
        return None
