"""
Daily Logger - 每日日志管理器
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .memory_db import MemoryDB

logger = logging.getLogger(__name__)


class DailyLogger:
    """
    每日日志管理器
    
    负责：
    - 记录每日事件
    - 按日期查询日志
    - 导出 Markdown
    """
    
    # 日志类型常量
    EVENT_TYPES = [
        'milestone',      # 里程碑
        'task',          # 任务
        'decision',      # 决策
        'insight',       # 洞察
        'problem',       # 问题
        'solution',      # 解决方案
        'learning',      # 学习
        'note',          # 笔记
        'reminder',      # 提醒
        'achievement'    # 成就
    ]
    
    def __init__(self, db: MemoryDB, log_dir: str = "memory"):
        """
        初始化每日日志管理器
        
        Args:
            db: MemoryDB 实例
            log_dir: 日志目录（默认: memory）
        """
        self.db = db
        self.log_dir = Path(log_dir)
        self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """确保日志目录存在"""
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_event(
        self,
        date: str,
        event_type: str,
        content: Dict[str, Any],
        importance: int = 5,
        tags: Optional[List[str]] = None
    ) -> int:
        """
        记录每日事件
        
        Args:
            date: 日期 (YYYY-MM-DD)
            event_type: 事件类型
            content: 事件内容
            importance: 重要性 0-10
            tags: 标签列表
        
        Returns:
            记忆ID
        """
        if event_type not in self.EVENT_TYPES:
            logger.warning(f"未知事件类型: {event_type}，使用 'note'")
            event_type = 'note'
        
        # 验证日期格式
        self._validate_date(date)
        
        event = {
            "type": "daily_event",
            "event_type": event_type,
            "title": content.get("title", "无标题"),
            "description": content.get("description", ""),
            "details": content.get("details", {}),
            "date": date,
            "logged_at": datetime.now().isoformat()
        }
        
        return self.db.save_memory(
            memory_type='daily',
            date=date,
            content=event,
            importance=importance,
            tags=tags or [event_type]
        )
    
    def get_daily_log(self, date: str) -> List[Dict[str, Any]]:
        """
        获取某天的日志
        
        Args:
            date: 日期 (YYYY-MM-DD)
        
        Returns:
            事件列表
        """
        self._validate_date(date)
        
        memories = self.db.get_memories(
            memory_type='daily',
            date=date,
            limit=1000
        )
        
        events = []
        for m in memories:
            content = m.get('content', {})
            if content.get('type') == 'daily_event':
                events.append({
                    'id': m['id'],
                    'event_type': content.get('event_type'),
                    'title': content.get('title'),
                    'description': content.get('description'),
                    'details': content.get('details', {}),
                    'importance': m['importance'],
                    'tags': m['tags'],
                    'created_at': m['created_at']
                })
        
        return sorted(events, key=lambda x: x['created_at'])
    
    def get_recent_events(
        self,
        days: int = 7,
        importance_threshold: int = 5,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取最近的重要事件
        
        Args:
            days: 天数
            importance_threshold: 重要性阈值
            event_type: 事件类型过滤
        
        Returns:
            事件列表
        """
        memories = self.db.get_memories(
            memory_type='daily',
            limit=1000
        )
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        events = []
        for m in memories:
            content = m.get('content', {})
            if content.get('type') != 'daily_event':
                continue
            
            # 过滤条件
            if event_type and content.get('event_type') != event_type:
                continue
            if m['importance'] < importance_threshold:
                continue
            if m.get('date', '') < cutoff_date:
                continue
            
            events.append({
                'id': m['id'],
                'event_type': content.get('event_type'),
                'title': content.get('title'),
                'description': content.get('description'),
                'importance': m['importance'],
                'tags': m['tags'],
                'date': m.get('date'),
                'created_at': m['created_at']
            })
        
        return sorted(events, key=lambda x: (x['importance'], x['created_at']), reverse=True)
    
    def export_to_markdown(
        self,
        date: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        导出某天日志为 Markdown 格式
        
        Args:
            date: 日期 (YYYY-MM-DD)
            output_path: 输出文件路径（可选）
        
        Returns:
            Markdown 内容
        """
        self._validate_date(date)
        
        events = self.get_daily_log(date)
        
        # 按事件类型分组
        by_type = {}
        for event in events:
            etype = event['event_type']
            if etype not in by_type:
                by_type[etype] = []
            by_type[etype].append(event)
        
        # 构建 Markdown
        md_lines = [
            f"# Daily Log - {date}",
            "",
            f"**总事件数**: {len(events)}",
            "",
            "---",
            ""
        ]
        
        # 重要性徽章
        def importance_badge(level: int) -> str:
            if level >= 8:
                return "🔴"
            elif level >= 5:
                return "🟡"
            else:
                return "🟢"
        
        # 按类型输出
        for event_type in self.EVENT_TYPES:
            if event_type not in by_type:
                continue
            
            md_lines.append(f"## {event_type.upper()}")
            md_lines.append("")
            
            for event in by_type[event_type]:
                md_lines.append(f"- {importance_badge(event['importance'])} **{event['title']}**")
                if event['description']:
                    md_lines.append(f"  - {event['description']}")
                md_lines.append("")
        
        md_content = "\n".join(md_lines)
        
        # 保存到文件
        if output_path:
            output_path = Path(output_path).expanduser()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            logger.info(f"导出日志到: {output_path}")
        
        return md_content
    
    def get_log_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        获取日志统计
        
        Args:
            days: 天数
        
        Returns:
            统计信息
        """
        memories = self.db.get_memories(
            memory_type='daily',
            limit=10000
        )
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # 过滤
        events = [m for m in memories if m.get('date', '') >= cutoff_date]
        
        # 按类型统计
        by_type = {}
        total_importance = 0
        
        for m in events:
            content = m.get('content', {})
            etype = content.get('event_type', 'unknown')
            by_type[etype] = by_type.get(etype, 0) + 1
            total_importance += m['importance']
        
        return {
            'total_events': len(events),
            'by_type': by_type,
            'avg_importance': total_importance / len(events) if events else 0,
            'days_covered': days
        }
    
    def _validate_date(self, date: str) -> None:
        """验证日期格式"""
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"无效的日期格式: {date}，期望 YYYY-MM-DD")
    
    def get_today_log(self) -> List[Dict[str, Any]]:
        """获取今天的日志"""
        return self.get_daily_log(datetime.now().strftime("%Y-%m-%d"))
    
    def log_milestone(
        self,
        title: str,
        description: str = "",
        importance: int = 9,
        tags: Optional[List[str]] = None
    ) -> int:
        """
        快速记录里程碑
        
        Args:
            title: 里程碑标题
            description: 描述
            importance: 重要性
            tags: 标签
        
        Returns:
            记忆ID
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_event(
            date=today,
            event_type='milestone',
            content={
                "title": title,
                "description": description,
                "details": {"recorded_by": "Local Memory System V3"}
            },
            importance=importance,
            tags=tags or ['milestone', 'achievement']
        )
