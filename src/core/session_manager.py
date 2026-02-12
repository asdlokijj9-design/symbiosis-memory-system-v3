"""
Session Manager - 会话上下文管理器
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from .memory_db import MemoryDB

logger = logging.getLogger(__name__)


class SessionManager:
    """
    会话上下文管理器
    
    负责：
    - 保存/加载会话上下文到 .session_context.txt
    - 记录对话历史
    - 会话历史管理
    """
    
    # 默认上下文文件路径
    DEFAULT_CONTEXT_PATH = "~/.openclaw/workspace/.session_context.txt"
    
    # 上下文文件模板
    CONTEXT_TEMPLATE = {
        "session_id": None,
        "created_at": None,
        "last_active": None,
        "summary": None,
        "important_topics": [],
        "pending_actions": [],
        "mood": None,
        "conversation_history": []
    }
    
    def __init__(self, db: MemoryDB):
        """
        初始化会话管理器
        
        Args:
            db: MemoryDB 实例
        """
        self.db = db
        self._ensure_context_directory()
    
    def _ensure_context_directory(self):
        """确保上下文目录存在"""
        path = Path(self.DEFAULT_CONTEXT_PATH).expanduser()
        parent = path.parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
    
    def _resolve_path(self, path: str) -> str:
        """解析路径"""
        return os.path.expanduser(path)
    
    def save_session_context(
        self,
        session_id: str,
        context: Dict[str, Any],
        file_path: Optional[str] = None
    ) -> bool:
        """
        保存会话上下文
        
        Args:
            session_id: 会话ID
            context: 上下文内容
            file_path: 文件路径（默认: ~/.openclaw/workspace/.session_context.txt）
        
        Returns:
            是否成功
        """
        if file_path is None:
            file_path = self.DEFAULT_CONTEXT_PATH
        
        file_path = self._resolve_path(file_path)
        
        # 构建完整上下文
        full_context = {
            **self.CONTEXT_TEMPLATE,
            **context,
            "session_id": session_id,
            "last_active": datetime.now().isoformat()
        }
        
        try:
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(full_context, f, ensure_ascii=False, indent=2)
            
            # 保存到数据库
            self.db.save_memory(
                memory_type='session',
                session_id=session_id,
                content=full_context,
                importance=self._calculate_importance(full_context)
            )
            
            logger.info(f"保存会话上下文: {session_id}")
            return True
        
        except Exception as e:
            logger.error(f"保存会话上下文失败: {e}")
            return False
    
    def load_session_context(
        self,
        file_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        加载会话上下文
        
        Args:
            file_path: 文件路径（默认: ~/.openclaw/workspace/.session_context.txt）
        
        Returns:
            上下文内容，不存在则返回 None
        """
        if file_path is None:
            file_path = self.DEFAULT_CONTEXT_PATH
        
        file_path = self._resolve_path(file_path)
        
        if not os.path.exists(file_path):
            logger.debug(f"上下文文件不存在: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        except json.JSONDecodeError as e:
            logger.error(f"解析上下文文件失败: {e}")
            return None
        except Exception as e:
            logger.error(f"加载上下文文件失败: {e}")
            return None
    
    def save_conversation(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        timestamp: Optional[str] = None
    ) -> int:
        """
        保存单条对话记录
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            assistant_response: 助手回复
            timestamp: 时间戳（可选，默认当前时间）
        
        Returns:
            记忆ID
        """
        conversation = {
            "type": "conversation",
            "user_message": user_message,
            "assistant_response": assistant_response,
            "timestamp": timestamp or datetime.now().isoformat()
        }
        
        return self.db.save_memory(
            memory_type='session',
            session_id=session_id,
            content=conversation,
            importance=self._calculate_conversation_importance(user_message)
        )
    
    def get_conversation_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取对话历史
        
        Args:
            session_id: 会话ID（可选，不传则获取所有）
            limit: 返回数量限制
        
        Returns:
            对话历史列表
        """
        memories = self.db.get_memories(
            memory_type='session',
            session_id=session_id,
            limit=limit
        )
        
        # 过滤对话类型的记忆
        conversations = []
        for m in memories:
            content = m.get('content', {})
            if content.get('type') == 'conversation':
                conversations.append({
                    'id': m['id'],
                    'session_id': m['session_id'],
                    'user_message': content.get('user_message'),
                    'assistant_response': content.get('assistant_response'),
                    'timestamp': content.get('timestamp'),
                    'created_at': m['created_at']
                })
        
        return conversations
    
    def get_session_history(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取会话历史列表
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            会话历史列表（每个会话最新一条）
        """
        memories = self.db.get_memories(
            memory_type='session',
            limit=limit * 2,  # 获取更多，过滤重复
            offset=offset
        )
        
        # 按 session_id 去重，只保留最新的
        latest_by_session = {}
        for m in memories:
            sid = m.get('session_id')
            if sid and sid not in latest_by_session:
                latest_by_session[sid] = {
                    'session_id': sid,
                    'content': m['content'],
                    'created_at': m['created_at'],
                    'updated_at': m['updated_at']
                }
        
        return list(latest_by_session.values())[:limit]
    
    def update_conversation_context(
        self,
        session_id: str,
        new_messages: List[Dict[str, str]]
    ) -> bool:
        """
        更新对话上下文（追加新消息）
        
        Args:
            session_id: 会话ID
            new_messages: 新消息列表 [{'role': 'user'|'assistant', 'content': ...}]
        
        Returns:
            是否成功
        """
        # 加载现有上下文
        context = self.load_session_context()
        if not context:
            context = {
                "session_id": session_id,
                "conversation_history": []
            }
        
        # 追加新消息
        for msg in new_messages:
            context["conversation_history"].append({
                **msg,
                "timestamp": datetime.now().isoformat()
            })
        
        # 限制历史长度
        max_history = 100
        if len(context["conversation_history"]) > max_history:
            context["conversation_history"] = context["conversation_history"][-max_history:]
        
        # 保存
        return self.save_session_context(session_id, context)
    
    def create_session(
        self,
        session_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        创建新会话
        
        Args:
            session_id: 会话ID
            initial_context: 初始上下文
        
        Returns:
            是否成功
        """
        context = {
            **(initial_context or {}),
            "created_at": datetime.now().isoformat(),
            "summary": initial_context.get("summary", "新会话"),
            "mood": "neutral"
        }
        
        return self.save_session_context(session_id, context)
    
    def end_session(
        self,
        session_id: str,
        summary: Optional[str] = None
    ) -> bool:
        """
        结束会话
        
        Args:
            session_id: 会话ID
            summary: 会话总结
        
        Returns:
            是否成功
        """
        context = self.load_session_context()
        if not context:
            return False
        
        if summary:
            context["summary"] = summary
        
        context["ended_at"] = datetime.now().isoformat()
        
        return self.save_session_context(session_id, context)
    
    def _calculate_importance(self, context: Dict[str, Any]) -> int:
        """计算上下文重要性"""
        importance = 5  # 默认分数
        
        # 根据内容调整
        if context.get("important_topics"):
            importance += 2
        if context.get("pending_actions"):
            importance += 1
        if context.get("mood"):
            importance += 1
        
        # 钳制在 0-10 之间
        return max(0, min(10, importance))
    
    def _calculate_conversation_importance(self, user_message: str) -> int:
        """计算对话重要性"""
        importance = 3  # 默认分数
        
        # 根据关键词调整
        important_keywords = ["重要", "记住", "关键", "里程碑", "目标", "永久"]
        for keyword in important_keywords:
            if keyword in user_message:
                importance += 2
                break
        
        # 钳制在 0-10 之间
        return max(0, min(10, importance))
