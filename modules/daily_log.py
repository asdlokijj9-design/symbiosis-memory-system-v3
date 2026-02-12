"""
每日日志模块 - 自动记录每日发生的事情
"""

from typing import Optional
from datetime import datetime, date
from pathlib import Path
import json
import aiofiles


class DailyLogModule:
    """每日日志模块"""
    
    def __init__(self, log_dir: str = None):
        """初始化每日日志模块
        
        Args:
            log_dir: 日志目录路径
        """
        self.log_dir = Path(log_dir) if log_dir else Path.home() / ".openclaw" / "workspace" / "memory"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def get_log_path(self, log_date: date = None) -> Path:
        """获取日志文件路径
        
        Args:
            log_date: 日期，默认为今天
            
        Returns:
            日志文件路径
        """
        if log_date is None:
            log_date = date.today()
        return self.log_dir / f"{log_date.isoformat()}.md"
    
    async def append_entry(
        self,
        entry: str,
        category: str = "general",
        log_date: date = None
    ) -> dict:
        """追加日志条目
        
        Args:
            entry: 日志内容
            category: 日志分类
            log_date: 日期
            
        Returns:
            写入结果
        """
        log_path = self.get_log_path(log_date)
        timestamp = datetime.now().isoformat()
        
        formatted_entry = f"[{timestamp}] **[{category.upper()}]** {entry}\n"
        
        async with aiofiles.open(log_path, 'a', encoding='utf-8') as f:
            await f.write(formatted_entry)
        
        return {
            "success": True,
            "path": str(log_path),
            "timestamp": timestamp,
            "category": category
        }
    
    async def get_entries(
        self,
        start_date: date = None,
        end_date: date = None,
        category: str = None
    ) -> list:
        """获取日志条目
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            category: 分类筛选
            
        Returns:
            日志条目列表
        """
        entries = []
        
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = date.today()
        
        current = start_date
        while current <= end_date:
            log_path = self.get_log_path(current)
            if log_path.exists():
                async with aiofiles.open(log_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    lines = content.split('\n')
                    for line in lines:
                        if line.strip():
                            if category is None or category.upper() in line:
                                entries.append({
                                    "date": current.isoformat(),
                                    "content": line.strip()
                                })
            current = date.fromordinal(current.toordinal() + 1)
        
        return entries
    
    async def export_to_json(
        self,
        start_date: date = None,
        end_date: date = None
    ) -> dict:
        """导出为JSON格式
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            JSON格式的日志数据
        """
        entries = await self.get_entries(start_date, end_date)
        return {
            "exported_at": datetime.now().isoformat(),
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "entries": entries
        }
    
    async def summarize_day(self, log_date: date = None) -> dict:
        """总结一天的日志
        
        Args:
            log_date: 日期
            
        Returns:
            每日总结
        """
        entries = await self.get_entries(log_date=log_date)
        
        categories = {}
        for entry in entries:
            content = entry["content"]
            if "**[WORK]**" in content:
                categories.setdefault("work", []).append(entry)
            elif "**[LEARNING]**" in content:
                categories.setdefault("learning", []).append(entry)
            elif "**[PERSONAL]**" in content:
                categories.setdefault("personal", []).append(entry)
            else:
                categories.setdefault("general", []).append(entry)
        
        return {
            "date": (log_date or date.today()).isoformat(),
            "total_entries": len(entries),
            "categories": {
                cat: len(items) for cat, items in categories.items()
            },
            "entries": entries
        }
