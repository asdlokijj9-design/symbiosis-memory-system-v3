"""
Versioning Service - 版本化服务
"""

import logging
from typing import Optional, List, Dict, Any

from .memory_db import MemoryDB

logger = logging.getLogger(__name__)


class VersioningService:
    """
    版本化服务
    
    提供：
    - 版本历史查询
    - 版本对比
    - 版本恢复
    """
    
    def __init__(self, db: MemoryDB):
        """初始化版本化服务"""
        self.db = db
    
    def get_version_history(self, memory_id: int) -> List[Dict[str, Any]]:
        """
        获取记忆的完整版本历史
        
        Args:
            memory_id: 记忆ID
        
        Returns:
            版本历史列表
        """
        return self.db.get_versions(memory_id)
    
    def get_version_diff(
        self,
        memory_id: int,
        version_a: int,
        version_b: int
    ) -> Dict[str, Any]:
        """
        获取两个版本的差异
        
        Args:
            memory_id: 记忆ID
            version_a: 版本号A
            version_b: 版本号B
        
        Returns:
            差异信息
        """
        versions = self.db.get_versions(memory_id)
        version_map = {v['version']: v for v in versions}
        
        v_a = version_map.get(version_a)
        v_b = version_map.get(version_b)
        
        if not v_a or not v_b:
            return {'error': '版本不存在'}
        
        # 简单对比
        changes = {}
        all_keys = set(v_a['content'].keys()) | set(v_b['content'].keys())
        
        for key in all_keys:
            val_a = v_a['content'].get(key)
            val_b = v_b['content'].get(key)
            
            if val_a != val_b:
                changes[key] = {
                    'from': val_a,
                    'to': val_b
                }
        
        return {
            'version_a': version_a,
            'version_b': version_b,
            'changed_at_a': v_a['created_at'],
            'changed_at_b': v_b['created_at'],
            'changes': changes,
            'has_changes': bool(changes)
        }
    
    def get_latest_versions(
        self,
        memory_ids: Optional[List[int]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取最新版本（可用于仪表盘）
        
        Args:
            memory_ids: 记忆ID列表（可选）
            limit: 返回数量
        
        Returns:
            最新版本列表
        """
        if memory_ids:
            # 指定记忆ID
            results = []
            for mid in memory_ids[:limit]:
                versions = self.db.get_versions(mid)
                if versions:
                    results.append(versions[-1])  # 最新版本
            return results
        else:
            # 获取所有记忆的最新版本
            memories = self.db.get_memories(limit=limit * 2)
            results = []
            for m in memories:
                versions = self.db.get_versions(m['id'])
                if versions:
                    results.append({
                        'memory_id': m['id'],
                        'version': versions[-1],
                        'memory_type': m['memory_type'],
                        'importance': m['importance']
                    })
            return results[:limit]
    
    def compare_memories(
        self,
        memory_id_a: int,
        memory_id_b: int
    ) -> Dict[str, Any]:
        """
        比较两条记忆
        
        Args:
            memory_id_a: 记忆ID A
            memory_id_b: 记忆ID B
        
        Returns:
            比较结果
        """
        m_a = self.db.get_memory(memory_id_a)
        m_b = self.db.get_memory(memory_id_b)
        
        if not m_a or not m_b:
            return {'error': '记忆不存在'}
        
        return {
            'memory_a': {
                'id': m_a['id'],
                'type': m_a['memory_type'],
                'importance': m_a['importance'],
                'created_at': m_a['created_at']
            },
            'memory_b': {
                'id': m_b['id'],
                'type': m_b['memory_type'],
                'importance': m_b['importance'],
                'created_at': m_b['created_at']
            },
            'versions_a': len(self.db.get_versions(memory_id_a)),
            'versions_b': len(self.db.get_versions(memory_id_b))
        }
    
    def get_change_log(
        self,
        memory_id: int,
        changed_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取变更日志
        
        Args:
            memory_id: 记忆ID
            changed_by: 按变更者过滤
        
        Returns:
            变更历史
        """
        versions = self.db.get_versions(memory_id)
        
        if changed_by:
            versions = [v for v in versions if v['changed_by'] == changed_by]
        
        return versions
    
    def rollback_to_version(
        self,
        memory_id: int,
        version: int
    ) -> bool:
        """
        回滚到指定版本（实际上是恢复）
        
        Args:
            memory_id: 记忆ID
            version: 目标版本号
        
        Returns:
            是否成功
        """
        versions = self.db.get_versions(memory_id)
        target = next((v for v in versions if v['version'] == version), None)
        
        if not target:
            return False
        
        return self.db.restore_version(target['id'])
