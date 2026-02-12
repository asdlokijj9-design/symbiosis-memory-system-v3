"""
Backup Service - 本地备份服务
"""

import os
import shutil
import hashlib
import logging
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any

from .memory_db import MemoryDB

logger = logging.getLogger(__name__)


class BackupService:
    """
    本地备份服务
    
    功能：
    - 手动/自动备份
    - 备份验证
    - 备份恢复
    - 旧备份清理
    """
    
    def __init__(
        self,
        db: MemoryDB,
        backup_dir: str = "data/backups"
    ):
        """
        初始化备份服务
        
        Args:
            db: MemoryDB 实例
            backup_dir: 备份目录
        """
        self.db = db
        self.backup_dir = backup_dir
        self._ensure_backup_directory()
    
    def _ensure_backup_directory(self):
        """确保备份目录存在"""
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _generate_backup_filename(self, prefix: str = "backup") -> str:
        """生成备份文件名"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"{prefix}_{timestamp}"
    
    def _calculate_checksum(self, filepath: str) -> str:
        """计算文件校验和"""
        md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()
    
    def create_backup(
        self,
        backup_type: str = "auto",
        description: Optional[str] = None
    ) -> int:
        """
        创建备份
        
        Args:
            backup_type: 备份类型 ('scheduled', 'manual', 'auto')
            description: 描述
        
        Returns:
            备份ID
        """
        # 生成备份路径
        filename = self._generate_backup_filename()
        backup_path = os.path.join(self.backup_dir, f"{filename}.db")
        
        try:
            # 确保数据库已刷新
            if hasattr(self.db, 'conn') and self.db.conn:
                self.db.conn.commit()
            
            # 复制数据库文件
            shutil.copy2(self.db.db_path, backup_path)
            
            # 计算校验和
            checksum = self._calculate_checksum(backup_path)
            
            # 获取文件大小
            size_bytes = os.path.getsize(backup_path)
            
            # 记录备份
            backup_id = self.db.conn.execute("""
                INSERT INTO backups (backup_type, file_path, size_bytes, checksum, status, description)
                VALUES (?, ?, ?, ?, 'completed', ?)
            """, (backup_type, backup_path, size_bytes, checksum, description)).lastrowid
            
            self.db.conn.commit()
            
            logger.info(f"创建备份: ID={backup_id}, path={backup_path}")
            return backup_id
        
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            # 记录失败的备份
            if hasattr(self.db, 'conn') and self.db.conn:
                try:
                    self.db.conn.execute("""
                        INSERT INTO backups (backup_type, file_path, status, description)
                        VALUES (?, ?, 'failed', ?)
                    """, (backup_type, backup_path, str(e)))
                    self.db.conn.commit()
                except:
                    pass
            raise
    
    def create_backup_with_lock(
        self,
        backup_type: str = "auto",
        description: Optional[str] = None,
        timeout: float = 30.0
    ) -> int:
        """
        创建备份（带锁，防止并发）
        
        Args:
            backup_type: 备份类型
            description: 描述
            timeout: 超时时间
        
        Returns:
            备份ID
        """
        lock = threading.Lock()
        
        if lock.acquire(timeout=timeout):
            try:
                return self.create_backup(backup_type, description)
            finally:
                lock.release()
        else:
            raise TimeoutError("获取备份锁超时")
    
    def restore_backup(self, backup_id: int) -> bool:
        """
        从备份恢复
        
        Args:
            backup_id: 备份ID
        
        Returns:
            是否成功
        """
        # 获取备份信息
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT file_path, checksum, status FROM backups WHERE id = ?
        """, (backup_id,))
        
        row = cursor.fetchone()
        if not row:
            logger.error(f"备份不存在: {backup_id}")
            return False
        
        backup_path, expected_checksum, status = row[0]
        
        if status != 'completed':
            logger.error(f"备份状态异常: {status}")
            return False
        
        # 验证文件存在
        if not os.path.exists(backup_path):
            logger.error(f"备份文件不存在: {backup_path}")
            return False
        
        # 验证校验和
        actual_checksum = self._calculate_checksum(backup_path)
        if actual_checksum != expected_checksum:
            logger.error(f"备份校验和不匹配: {actual} != {expected}")
            return False
        
        # 关闭当前连接
        self.db.close()
        
        # 恢复文件
        try:
            shutil.copy2(backup_path, self.db.db_path)
            logger.info(f"从备份恢复成功: {backup_path}")
            
            # 重新连接
            self.db.connect()
            return True
        
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            # 尝试重新连接（即使恢复失败）
            try:
                self.db.connect()
            except:
                pass
            return False
    
    def verify_backup(self, backup_id: int) -> Dict[str, Any]:
        """
        验证备份完整性
        
        Args:
            backup_id: 备份ID
        
        Returns:
            验证结果
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT file_path, checksum, status, size_bytes, created_at
            FROM backups WHERE id = ?
        """, (backup_id,))
        
        row = cursor.fetchone()
        if not row:
            return {'valid': False, 'error': '备份不存在'}
        
        backup_path, expected_checksum, status, size_bytes, created_at = row
        
        result = {
            'backup_id': backup_id,
            'file_path': backup_path,
            'status': status,
            'size_bytes': size_bytes,
            'created_at': created_at,
            'valid': False
        }
        
        # 检查文件存在
        if not os.path.exists(backup_path):
            result['error'] = '文件不存在'
            return result
        
        # 验证校验和
        actual_checksum = self._calculate_checksum(backup_path)
        result['checksum_expected'] = expected_checksum
        result['checksum_actual'] = actual_checksum
        
        if actual_checksum == expected_checksum:
            result['valid'] = True
            result['error'] = None
        else:
            result['error'] = '校验和不匹配'
        
        return result
    
    def list_backups(
        self,
        backup_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        列出备份
        
        Args:
            backup_type: 按类型过滤
            status: 按状态过滤
            limit: 返回数量
        
        Returns:
            备份列表
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT id, backup_type, file_path, size_bytes, checksum, status, created_at, description
            FROM backups
            WHERE 1=1
        """
        params = []
        
        if backup_type:
            query += " AND backup_type = ?"
            params.append(backup_type)
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'backup_type': row[1],
                'file_path': row[2],
                'size_bytes': row[3],
                'checksum': row[4],
                'status': row[5],
                'created_at': row[6],
                'description': row[7]
            })
        
        return results
    
    def cleanup_old_backups(
        self,
        keep_count: int = 10,
        backup_type: Optional[str] = None
    ) -> int:
        """
        清理旧备份（保留最近 N 个）
        
        Args:
            keep_count: 保留数量
            backup_type: 只清理特定类型
        
        Returns:
            删除的备份数量
        """
        cursor = self.db.conn.cursor()
        
        # 获取要删除的备份
        query = """
            SELECT id, file_path FROM backups
            WHERE 1=1
        """
        params = []
        
        if backup_type:
            query += " AND backup_type = ?"
            params.append(backup_type)
        
        query += """
            AND id NOT IN (
                SELECT id FROM backups
                WHERE 1=1
        """
        params2 = []
        if backup_type:
            query += " AND backup_type = ?"
            params2.append(backup_type)
        
        query += f"""
                ORDER BY created_at DESC LIMIT {keep_count}
            )
            ORDER BY created_at ASC
        """
        
        cursor.execute(query, params + params2)
        to_delete = cursor.fetchall()
        
        deleted = 0
        for backup_id, file_path in to_delete:
            try:
                # 删除文件
                if os.path.exists(file_path):
                    os.unlink(file_path)
                
                # 删除记录
                cursor.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
                deleted += 1
            
            except Exception as e:
                logger.error(f"删除备份失败: {backup_id}, {e}")
        
        self.db.conn.commit()
        
        if deleted > 0:
            logger.info(f"清理了 {deleted} 个旧备份")
        
        return deleted
    
    def get_latest_backup(self) -> Optional[Dict[str, Any]]:
        """获取最新的备份"""
        backups = self.list_backups(limit=1)
        return backups[0] if backups else None
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """获取备份统计"""
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT backup_type, COUNT(*), AVG(size_bytes), MAX(created_at)
            FROM backups
            WHERE status = 'completed'
            GROUP BY backup_type
        """)
        
        by_type = {}
        for row in cursor.fetchall():
            by_type[row[0]] = {
                'count': row[1],
                'avg_size_bytes': row[2],
                'last_backup': row[3]
            }
        
        cursor.execute("SELECT COUNT(*) FROM backups WHERE status = 'failed'")
        failed_count = cursor.fetchone()[0]
        
        return {
            'by_type': by_type,
            'failed_count': failed_count,
            'total_size_bytes': sum(t['avg_size_bytes'] * t['count'] for t in by_type.values())
        }
