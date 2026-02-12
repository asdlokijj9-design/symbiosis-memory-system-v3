"""
SQLite 数据库核心模块
"""

import sqlite3
from datetime import datetime
from typing import Optional


class DatabaseCore:
    """SQLite 数据库核心"""
    
    def __init__(self, db_path: str = None):
        """初始化数据库
        
        Args:
            db_path: 数据库文件路径 (默认内存数据库)
        """
        self.db_path = db_path or ":memory:"
        self._connected = False
    
    async def initialize(self) -> None:
        """初始化数据库表结构"""
        if self._connected:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建会话表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT,
                updated_at TEXT,
                data BLOB
            )
        ''')
        
        # 创建记忆表
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
        
        # 创建每日日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                category TEXT,
                content TEXT,
                timestamp TEXT
            )
        ''')
        
        # 创建版本历史表
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
        
        # 创建索引（如果不存在）
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_category ON memory(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_logs_date ON daily_logs(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_entity ON versions(entity_type, entity_id)')
        
        conn.commit()
        conn.close()
        
        self._connected = True
    
    async def execute(self, query: str, params: tuple = None) -> list:
        """执行查询
        
        Args:
            query: SQL 查询
            params: 参数
            
        Returns:
            查询结果
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # 对于SELECT，fetchall返回结果；对于INSERT/UPDATE，需要commit
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
        else:
            conn.commit()
            results = cursor.fetchall() if query.strip().upper().startswith('INSERT RETURNING') else []
        
        conn.close()
        
        return results
    
    async def execute_many(self, query: str, params_list: list) -> None:
        """批量执行
        
        Args:
            query: SQL 查询
            params_list: 参数列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.executemany(query, params_list)
        
        conn.commit()
        conn.close()
    
    async def close(self) -> None:
        """关闭数据库连接"""
        self._connected = False
    
    async def vacuum(self) -> dict:
        """清理数据库
        
        Returns:
            清理结果
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('VACUUM')
        
        conn.close()
        
        return {"vacuumed": True, "at": datetime.now().isoformat()}
    
    async def get_stats(self) -> dict:
        """获取数据库统计
        
        Returns:
            统计信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        tables = ['sessions', 'memory', 'daily_logs', 'versions']
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[table] = cursor.fetchone()[0]
        
        cursor.execute('SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()')
        stats['size_bytes'] = cursor.fetchone()[0]
        
        conn.close()
        
        return stats
