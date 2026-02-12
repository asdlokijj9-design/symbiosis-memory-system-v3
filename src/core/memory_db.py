"""
Memory Database Core - SQLite 记忆数据库核心
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MemoryDB:
    """
    SQLite 记忆数据库核心类
    
    提供：
    - 记忆的 CRUD 操作
    - 版本化管理
    - 备份和恢复
    - 数据库完整性检查
    """
    
    def __init__(self, db_path: str = "data/memory.db"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径（默认: data/memory.db）
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._ensure_db_directory()
    
    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def connect(self) -> None:
        """建立数据库连接"""
        if self.conn is None:
            self.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level='IMMEDIATE'
            )
            # 启用外键约束
            self.conn.execute("PRAGMA foreign_keys = ON")
            # 设置行工厂为字典
            self.conn.row_factory = sqlite3.Row
    
    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        if not self.conn:
            self.connect()
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"事务回滚: {e}")
            raise
    
    def create_tables(self) -> None:
        """创建所有表（如果不存在）"""
        if not self.conn:
            self.connect()
        
        # 创建记忆表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT NOT NULL CHECK (memory_type IN ('session', 'daily', 'longterm')),
                session_id TEXT,
                date TEXT,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 0 CHECK (importance >= 0 AND importance <= 10),
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0
            )
        """)
        
        # 创建版本历史表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id INTEGER NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                changed_by TEXT DEFAULT 'user',
                change_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
            )
        """)
        
        # 创建备份记录表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_type TEXT NOT NULL CHECK (backup_type IN ('scheduled', 'manual', 'auto')),
                file_path TEXT NOT NULL,
                size_bytes INTEGER,
                checksum TEXT,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_date ON memories(date)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_versions_memory ON versions(memory_id)
        """)
        
        self.conn.commit()
        logger.info("数据库表创建完成")
    
    def save_memory(
        self,
        memory_type: str,
        content: Dict[str, Any],
        session_id: Optional[str] = None,
        date: Optional[str] = None,
        importance: int = 0,
        tags: Optional[List[str]] = None
    ) -> int:
        """
        保存记忆
        
        Args:
            memory_type: 记忆类型 ('session', 'daily', 'longterm')
            content: 记忆内容（字典，会序列化为 JSON）
            session_id: 会话ID（可选）
            date: 日期 YYYY-MM-DD（可选）
            importance: 重要性评分 0-10
            tags: 标签列表（可选）
        
        Returns:
            记忆ID
        
        Raises:
            ValueError: 参数验证失败
        """
        if not content:
            raise ValueError("记忆内容不能为空")
        
        if memory_type not in ('session', 'daily', 'longterm'):
            raise ValueError(f"无效的记忆类型: {memory_type}")
        
        if importance < 0 or importance > 10:
            raise ValueError("重要性评分必须在 0-10 之间")
        
        content_json = json.dumps(content, ensure_ascii=False)
        tags_str = ','.join(tags) if tags else None
        
        if not self.conn:
            self.connect()
        
        with self.transaction() as cursor:
            cursor.execute("""
                INSERT INTO memories (
                    memory_type, session_id, date, content, importance, tags
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (memory_type, session_id, date, content_json, importance, tags_str))
            
            memory_id = cursor.lastrowid
            
            # 创建初始版本
            cursor.execute("""
                INSERT INTO versions (memory_id, version, content, changed_by, change_reason)
                VALUES (?, 1, ?, 'system', 'Initial creation')
            """, (memory_id, content_json))
        
        logger.debug(f"保存记忆 ID={memory_id}, type={memory_type}")
        return memory_id
    
    def get_memory(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """获取单条记忆"""
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, memory_type, session_id, date, content, importance, tags,
                   created_at, updated_at
            FROM memories
            WHERE id = ? AND is_deleted = 0
        """, (memory_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'id': row['id'],
            'memory_type': row['memory_type'],
            'session_id': row['session_id'],
            'date': row['date'],
            'content': json.loads(row['content']),
            'importance': row['importance'],
            'tags': row['tags'].split(',') if row['tags'] else [],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }
    
    def get_memories(
        self,
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None,
        date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查询记忆列表
        
        Args:
            memory_type: 按类型过滤（可选）
            session_id: 按会话ID过滤（可选）
            date: 按日期过滤（可选）
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            记忆列表
        """
        if not self.conn:
            self.connect()
        
        query = """
            SELECT id, memory_type, session_id, date, content, importance, tags,
                   created_at, updated_at
            FROM memories
            WHERE is_deleted = 0
        """
        params = []
        
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if date:
            query += " AND date = ?"
            params.append(date)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'memory_type': row['memory_type'],
                'session_id': row['session_id'],
                'date': row['date'],
                'content': json.loads(row['content']),
                'importance': row['importance'],
                'tags': row['tags'].split(',') if row['tags'] else [],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        return results
    
    def update_memory(
        self,
        memory_id: int,
        content: Dict[str, Any],
        changed_by: str = "user",
        change_reason: Optional[str] = None
    ) -> bool:
        """
        更新记忆（自动创建新版本）
        
        Args:
            memory_id: 要更新的记忆ID
            content: 新的内容
            changed_by: 变更来源 ('user', 'auto_extraction', 'fusion')
            change_reason: 变更原因
        
        Returns:
            是否成功
        """
        if not content:
            raise ValueError("更新内容不能为空")
        
        if not self.conn:
            self.connect()
        
        # 获取当前版本号
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(version) FROM versions WHERE memory_id = ?", (memory_id,))
        result = cursor.fetchone()
        new_version = (result[0] or 0) + 1
        
        content_json = json.dumps(content, ensure_ascii=False)
        
        with self.transaction() as cursor:
            # 更新记忆
            cursor.execute("""
                UPDATE memories
                SET content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 0
            """, (content_json, memory_id))
            
            if cursor.rowcount == 0:
                return False
            
            # 创建新版本
            cursor.execute("""
                INSERT INTO versions (memory_id, version, content, changed_by, change_reason)
                VALUES (?, ?, ?, ?, ?)
            """, (memory_id, new_version, content_json, changed_by, change_reason))
        
        logger.debug(f"更新记忆 ID={memory_id} 到版本 {new_version}")
        return True
    
    def get_versions(self, memory_id: int) -> List[Dict[str, Any]]:
        """获取某条记忆的所有版本"""
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, memory_id, version, content, changed_by, change_reason, created_at
            FROM versions
            WHERE memory_id = ?
            ORDER BY version ASC
        """, (memory_id,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'memory_id': row['memory_id'],
                'version': row['version'],
                'content': json.loads(row['content']),
                'changed_by': row['changed_by'],
                'change_reason': row['change_reason'],
                'created_at': row['created_at']
            })
        
        return results
    
    def restore_version(self, version_id: int) -> bool:
        """恢复到指定版本"""
        if not self.conn:
            self.connect()
        
        # 获取版本信息
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT memory_id, content FROM versions WHERE id = ?
        """, (version_id,))
        
        row = cursor.fetchone()
        if not row:
            return False
        
        memory_id, content = row[0], row[1]
        
        # 恢复到该版本
        return self.update_memory(
            memory_id,
            json.loads(content),
            changed_by='system',
            change_reason=f'Restored from version {version_id}'
        )
    
    def create_backup(self, backup_type: str = "auto") -> int:
        """创建备份"""
        if not self.conn:
            self.connect()
        
        # 执行完整性检查
        cursor = self.conn.cursor()
        
        # 获取数据库统计
        cursor.execute("SELECT COUNT(*) FROM memories")
        memory_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM versions")
        version_count = cursor.fetchone()[0]
        
        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = "data/backups"
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
        
        # 复制数据库文件
        import shutil
        shutil.copy2(self.db_path, backup_path)
        
        # 计算校验和
        import hashlib
        with open(backup_path, 'rb') as f:
            checksum = hashlib.md5(f.read()).hexdigest()
        
        # 获取文件大小
        size_bytes = os.path.getsize(backup_path)
        
        # 记录备份
        cursor.execute("""
            INSERT INTO backups (backup_type, file_path, size_bytes, checksum, status)
            VALUES (?, ?, ?, ?, 'completed')
        """, (backup_type, backup_path, size_bytes, checksum))
        
        backup_id = cursor.lastrowid
        self.conn.commit()
        
        logger.info(f"创建备份 ID={backup_id}, path={backup_path}")
        return backup_id
    
    def restore_backup(self, backup_id: int) -> bool:
        """从备份恢复"""
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT file_path FROM backups WHERE id = ?
        """, (backup_id,))
        
        row = cursor.fetchone()
        if not row:
            return False
        
        backup_path = row[0]
        
        if not os.path.exists(backup_path):
            logger.error(f"备份文件不存在: {backup_path}")
            return False
        
        # 验证校验和
        import hashlib
        with open(backup_path, 'rb') as f:
            checksum = hashlib.md5(f.read()).hexdigest()
        
        cursor.execute("SELECT checksum FROM backups WHERE id = ?", (backup_id,))
        expected = cursor.fetchone()[0]
        
        if checksum != expected:
            logger.error(f"备份校验和不匹配: {checksum} != {expected}")
            return False
        
        # 关闭当前连接
        self.close()
        
        # 恢复文件
        import shutil
        shutil.copy2(backup_path, self.db_path)
        
        # 重新连接
        self.connect()
        
        logger.info(f"从备份 ID={backup_id} 恢复成功")
        return True
    
    def list_backups(
        self,
        backup_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """列出备份"""
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        query = """
            SELECT id, backup_type, file_path, size_bytes, checksum, status, created_at
            FROM backups
        """
        params = []
        
        if backup_type:
            query += " WHERE backup_type = ?"
            params.append(backup_type)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'backup_type': row['backup_type'],
                'file_path': row['file_path'],
                'size_bytes': row['size_bytes'],
                'checksum': row['checksum'],
                'status': row['status'],
                'created_at': row['created_at']
            })
        
        return results
    
    def check_integrity(self) -> Dict[str, Any]:
        """检查数据库完整性"""
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master WHERE type='table' AND name IN ('memories', 'versions', 'backups')
        """)
        tables = [r[0] for r in cursor.fetchall()]
        
        # 获取各表记录数
        stats = {}
        for table in ['memories', 'versions', 'backups']:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats[table] = {'count': count}
            except sqlite3.OperationalError:
                stats[table] = {'count': 0, 'error': '表不存在'}
        
        # 运行 SQLite 完整性检查
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]
        
        return {
            'status': 'ok' if integrity_result == 'ok' else 'error',
            'tables_found': tables,
            'tables': stats,
            'integrity_check': integrity_result
        }
    
    def delete_memory(self, memory_id: int, permanent: bool = False) -> bool:
        """删除记忆"""
        if not self.conn:
            self.connect()
        
        if permanent:
            # 永久删除
            with self.transaction() as cursor:
                # 删除版本
                cursor.execute("DELETE FROM versions WHERE memory_id = ?", (memory_id,))
                # 删除记忆
                cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        else:
            # 软删除
            cursor.execute("""
                UPDATE memories SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (memory_id,))
        
        return cursor.rowcount > 0
