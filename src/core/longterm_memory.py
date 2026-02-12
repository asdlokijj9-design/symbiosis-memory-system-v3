"""
Longterm Memory - 长期记忆管理器
"""

import json
import logging
from typing import Optional, List, Dict, Any

from .memory_db import MemoryDB

logger = logging.getLogger(__name__)


class LongtermMemory:
    """
    长期记忆管理器
    
    负责：
    - 重要信息的长期保存
    - 智能提取和归档
    - 记忆搜索
    - 记忆融合
    """
    
    # 重要性阈值
    EXTRACTION_THRESHOLD = 7
    ARCHIVE_THRESHOLD = 8
    
    def __init__(self, db: MemoryDB):
        """初始化长期记忆管理器"""
        self.db = db
    
    def save_longterm_memory(
        self,
        content: Dict[str, Any],
        importance: int = 8,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None
    ) -> int:
        """
        直接保存长期记忆
        
        Args:
            content: 记忆内容
            importance: 重要性 0-10
            tags: 标签列表
            source: 来源 (可选)
        
        Returns:
            记忆ID
        """
        memory = {
            "type": "longterm_memory",
            "content": content,
            "source": source,
            "archived_at": None  # 如果从日志提取，这里会记录原始ID
        }
        
        return self.db.save_memory(
            memory_type='longterm',
            content=memory,
            importance=importance,
            tags=tags or []
        )
    
    def extract_and_archive(
        self,
        daily_log_ids: List[int],
        destination: str = "MEMORY.md",
        threshold: int = None
    ) -> int:
        """
        从每日日志中提取重要信息并归档
        
        Args:
            daily_log_ids: 每日日志ID列表
            destination: 目标文件（未使用，保留兼容）
            threshold: 重要性阈值（默认: ARCHIVE_THRESHOLD）
        
        Returns:
            归档的记忆ID数量
        """
        if threshold is None:
            threshold = self.ARCHIVE_THRESHOLD
        
        archived_count = 0
        
        for log_id in daily_log_ids:
            memory = self.db.get_memory(log_id)
            if not memory:
                continue
            
            content = memory.get('content', {})
            if content.get('type') != 'daily_event':
                continue
            
            # 只归档重要的
            if memory['importance'] < threshold:
                continue
            
            # 提取内容
            extracted = {
                "type": "extracted_memory",
                "original_event_type": content.get('event_type'),
                "title": content.get('title'),
                "description": content.get('description'),
                "details": content.get('details', {}),
                "original_id": log_id,
                "importance": memory['importance'],
                "extracted_at": self._get_timestamp()
            }
            
            # 保存为长期记忆
            self.save_longterm_memory(
                content=extracted,
                importance=memory['importance'],
                tags=memory['tags'],
                source=f"daily_log_{log_id}"
            )
            
            archived_count += 1
        
        logger.info(f"从 {len(daily_log_ids)} 条日志中归档了 {archived_count} 条重要信息")
        return archived_count
    
    def search_memories(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        importance_min: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索长期记忆
        
        Args:
            query: 搜索关键词（会在 content JSON 中搜索）
            tags: 标签过滤
            importance_min: 最低重要性
            limit: 返回数量
        
        Returns:
            记忆列表
        """
        memories = self.db.get_memories(
            memory_type='longterm',
            limit=limit * 2  # 获取更多，后过滤
        )
        
        results = []
        for m in memories:
            # 过滤重要性
            if m['importance'] < importance_min:
                continue
            
            # 过滤标签
            if tags:
                if not any(tag in m['tags'] for tag in tags):
                    continue
            
            # 搜索关键词
            if query:
                content_str = json.dumps(m['content'], ensure_ascii=False)
                if query.lower() not in content_str.lower():
                    continue
            
            results.append({
                'id': m['id'],
                'content': m['content'],
                'importance': m['importance'],
                'tags': m['tags'],
                'source': m['content'].get('source'),
                'created_at': m['created_at']
            })
        
        return results[:limit]
    
    def get_memory_graph(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        获取记忆图谱（按时间/标签组织）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制数量
        
        Returns:
            记忆图谱
        """
        memories = self.db.get_memories(
            memory_type='longterm',
            limit=limit
        )
        
        # 按标签分组
        by_tag = {}
        for m in memories:
            for tag in m['tags']:
                if tag not in by_tag:
                    by_tag[tag] = []
                by_tag[tag].append({
                    'id': m['id'],
                    'content': m['content'],
                    'importance': m['importance'],
                    'created_at': m['created_at']
                })
        
        # 按时间排序
        by_time = sorted(
            memories,
            key=lambda x: x['created_at'],
            reverse=True
        )
        
        return {
            'by_tag': by_tag,
            'by_time': by_time,
            'total_count': len(memories)
        }
    
    def merge_memories(
        self,
        memory_ids: List[int],
        strategy: str = "keep_all"
    ) -> int:
        """
        合并多条记忆
        
        Args:
            memory_ids: 记忆ID列表
            strategy: 合并策略
                - 'keep_all': 保留所有版本
                - 'merge_content': 合并内容
                - 'keep_latest': 只保留最新
        
        Returns:
            新记忆ID
        """
        if len(memory_ids) < 2:
            return memory_ids[0] if memory_ids else None
        
        memories = []
        for mid in memory_ids:
            m = self.db.get_memory(mid)
            if m:
                memories.append(m)
        
        if not memories:
            return None
        
        if strategy == "keep_all":
            # 保留所有版本作为引用
            merged_content = {
                "type": "merged_memory",
                "merged_from": memory_ids,
                "versions": [m['content'] for m in memories],
                "merged_at": self._get_timestamp()
            }
        elif strategy == "merge_content":
            # 合并内容（浅合并）
            merged = {}
            for m in memories:
                merged.update(m['content'])
            merged_content = {
                "type": "merged_memory",
                "merged_from": memory_ids,
                "content": merged,
                "merged_at": self._get_timestamp()
            }
        else:  # keep_latest
            latest = max(memories, key=lambda x: x['created_at'])
            merged_content = {
                "type": "merged_memory",
                "merged_from": memory_ids,
                "content": latest['content'],
                "merged_at": self._get_timestamp()
            }
        
        return self.save_longterm_memory(
            content=merged_content,
            importance=max(m['importance'] for m in memories),
            tags=list(set(tag for m in memories for tag in m['tags']))
        )
    
    def get_important_memories(
        self,
        min_importance: int = 8,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取最重要的记忆"""
        return self.search_memories(
            importance_min=min_importance,
            limit=limit
        )
    
    def add_tag(self, memory_id: int, tag: str) -> bool:
        """给记忆添加标签"""
        memory = self.db.get_memory(memory_id)
        if not memory:
            return False
        
        new_tags = set(memory['tags'])
        new_tags.add(tag)
        
        return self.db.update_memory(
            memory_id,
            content=memory['content'],
            changed_by='user',
            change_reason=f'Added tag: {tag}'
        )
    
    def remove_tag(self, memory_id: int, tag: str) -> bool:
        """移除记忆的标签"""
        memory = self.db.get_memory(memory_id)
        if not memory:
            return False
        
        new_tags = set(memory['tags'])
        new_tags.discard(tag)
        
        # 需要更新 tags 字段，但这需要特殊处理
        # 简化起见，这里只更新 content
        return False
    
    def export_to_memory_file(
        self,
        output_path: str = "~/workspace/MEMORY.md"
    ) -> bool:
        """
        导出所有长期记忆到 MEMORY.md
        
        Args:
            output_path: 输出路径
        
        Returns:
            是否成功
        """
        import os
        
        memories = self.search_memories(limit=1000)
        
        lines = [
            "# 🧠 第二大脑 - 长期记忆",
            "",
            f"*自动生成: {self._get_timestamp()}*",
            "",
            "---",
            ""
        ]
        
        # 按重要性排序
        memories.sort(key=lambda x: x['importance'], reverse=True)
        
        for m in memories:
            lines.append(f"## {m['content'].get('title', '无标题')}")
            lines.append("")
            lines.append(f"**重要性**: {'⭐' * m['importance']}")
            lines.append("")
            if m['tags']:
                lines.append(f"**标签**: {', '.join(m['tags'])}")
                lines.append("")
            lines.append(f"**内容**: {m['content']}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        content = "\n".join(lines)
        
        # 写入文件
        output_path = os.path.expanduser(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"导出长期记忆到: {output_path}")
        return True
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
