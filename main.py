"""
共生记忆系统 共生记忆 主入口
"""

from typing import Optional
from datetime import datetime
import asyncio

# 使用绝对导入
from core.database import DatabaseCore
from services.versioning_service import VersioningService
from services.persistence_service import PersistenceService
from services.backup_service import BackupService
from services.merging_service import MergingService
from services.real_time_service import RealTimeService
from modules.daily_log import DailyLogModule
from modules.longterm_memory import LongtermMemoryModule


class SymbiosisMemory:
    """
    共生记忆系统 V3
    
    核心功能：
    1. 跨会话记忆 - 自动保存/加载对话历史
    2. 每日日志 - 自动记录每天发生的事情
    3. 长期记忆 - 重要信息自动沉淀到 MEMORY.md
    4. 版本化 - 保留所有历史版本，支持回溯
    5. 实时持久化 - 每次对话后立即写入
    6. 本地备份 - 自动备份机制
    """
    
    def __init__(self, db_path: str = None):
        """初始化系统
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path or ":memory:"
        
        # 初始化所有服务
        self.versioning = None
        self.persistence = None
        self.backup = None
        self.merging = None
        self.real_time = None
        
        self.daily_log = None
        self.longterm_memory = None
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化所有模块"""
        if self._initialized:
            return
        
        # 初始化数据库核心
        db_core = DatabaseCore(self.db_path)
        await db_core.initialize()
        
        # 初始化服务
        self.versioning = VersioningService(self.db_path)
        self.persistence = PersistenceService(self.db_path)
        self.backup = BackupService(self.db_path)
        self.merging = MergingService(self.db_path)
        self.real_time = RealTimeService(self.db_path)
        
        # 初始化模块
        self.daily_log = DailyLogModule()
        self.longterm_memory = LongtermMemoryModule()
        
        self._initialized = True
    
    async def save_session_context(
        self,
        session_id: str,
        context: dict
    ) -> dict:
        """保存会话上下文
        
        Args:
            session_id: 会话ID
            context: 上下文数据
            
        Returns:
            保存结果
        """
        await self.initialize()
        
        # 版本化保存
        version_result = await self.versioning.create_version(
            "session",
            session_id,
            context
        )
        
        # 持久化保存
        persist_result = await self.persistence.save_session(
            session_id,
            context
        )
        
        # 实时通知
        await self.real_time.buffer_update({
            "type": "session_saved",
            "session_id": session_id,
            "version": version_result["version"]
        })
        
        return {
            "success": True,
            "session_id": session_id,
            "version": version_result["version"],
            "saved_at": version_result["created_at"]
        }
    
    async def load_session_context(
        self,
        session_id: str
    ) -> Optional[dict]:
        """加载会话上下文
        
        Args:
            session_id: 会话ID
            
        Returns:
            上下文数据
        """
        await self.initialize()
        
        version = await self.versioning.get_version("session", session_id)
        
        if version:
            return version["data"]
        
        return None
    
    async def get_all_sessions(self) -> list:
        """获取所有会话
        
        Returns:
            会话列表
        """
        await self.initialize()
        
        return await self.persistence.get_all_sessions()
    
    async def log_interaction(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        category: str = "general"
    ) -> dict:
        """记录交互
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            assistant_message: 助手回复
            category: 分类
            
        Returns:
            记录结果
        """
        await self.initialize()
        
        # 保存到每日日志
        log_result = await self.daily_log.append_entry(
            f"[{session_id}] {user_message[:50]}... | {assistant_message[:50]}...",
            category=category
        )
        
        # 版本化保存交互
        await self.versioning.create_version(
            "interaction",
            f"{session_id}_{datetime.now().isoformat()}",
            {
                "user_message": user_message,
                "assistant_message": assistant_message,
                "category": category
            }
        )
        
        return {
            "success": True,
            "logged_at": log_result["timestamp"]
        }
    
    async def add_longterm_memory(
        self,
        category: str,
        content: str,
        priority: int = 5,
        tags: list = None
    ) -> dict:
        """添加长期记忆
        
        Args:
            category: 分类
            content: 内容
            priority: 优先级
            tags: 标签
            
        Returns:
            添加结果
        """
        await self.initialize()
        
        # 添加到数据库
        db_result = await self.persistence.save_memory(
            category, content, priority, tags
        )
        
        # 添加到MEMORY.md
        md_result = await self.longterm_memory.add_memory(
            category, content, priority, tags
        )
        
        # 版本化
        await self.versioning.create_version(
            "memory",
            f"{category}_{datetime.now().isoformat()}",
            {"category": category, "content": content, "priority": priority}
        )
        
        return {
            "success": True,
            "db_saved": db_result["saved_at"],
            "md_saved": md_result["timestamp"]
        }
    
    async def create_backup(self) -> dict:
        """创建备份
        
        Returns:
            备份结果
        """
        await self.initialize()
        
        return await self.backup.create_backup()
    
    async def restore_backup(self, backup_path: str = None) -> dict:
        """恢复备份
        
        Args:
            backup_path: 备份路径
            
        Returns:
            恢复结果
        """
        await self.initialize()
        
        return await self.backup.restore_backup(backup_path)
    
    async def close(self) -> None:
        """关闭系统"""
        if self.real_time:
            await self.real_time.close()
        if self.persistence:
            await self.persistence.close()
    
    async def health_check(self) -> dict:
        """健康检查
        
        Returns:
            系统状态
        """
        return {
            "status": "healthy",
            "initialized": self._initialized,
            "db_path": self.db_path,
            "timestamp": datetime.now().isoformat()
        }


# 全局实例
_system_instance: Optional[SymbiosisMemory] = None


async def get_system(db_path: str = None) -> SymbiosisMemory:
    """获取系统实例（单例模式）
    
    Args:
        db_path: 数据库路径
        
    Returns:
        系统实例
    """
    global _system_instance
    
    if _system_instance is None:
        _system_instance = SymbiosisMemory(db_path)
        await _system_instance.initialize()
    
    return _system_instance


async def save_context(
    session_id: str,
    context: dict,
    db_path: str = None
) -> dict:
    """便捷函数：保存会话上下文
    
    Args:
        session_id: 会话ID
        context: 上下文
        db_path: 数据库路径
        
    Returns:
        保存结果
    """
    system = await get_system(db_path)
    return await system.save_session_context(session_id, context)


async def load_context(
    session_id: str,
    db_path: str = None
) -> Optional[dict]:
    """便捷函数：加载会话上下文
    
    Args:
        session_id: 会话ID
        db_path: 数据库路径
        
    Returns:
        上下文数据
    """
    system = await get_system(db_path)
    return await system.load_session_context(session_id)
