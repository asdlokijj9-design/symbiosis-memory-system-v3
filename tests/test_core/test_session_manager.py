# Tests - Session Manager
import pytest
import json
import os
import sys
import tempfile
import asyncio
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.persistence_service import PersistenceService
from services.versioning_service import VersioningService


class TestSessionManager:
    """测试会话管理器"""
    
    @pytest.fixture
    def db_path(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)
    
    @pytest.fixture
    def persistence(self, db_path):
        """创建持久化服务"""
        service = PersistenceService(db_path)
        return service
    
    @pytest.fixture
    def versioning(self, db_path):
        """创建版本控制服务"""
        return VersioningService(db_path)
    
    @pytest.mark.asyncio
    async def test_save_session_context(self, persistence):
        """测试保存会话上下文"""
        session_id = "test_session_001"
        context = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            "created_at": datetime.now().isoformat()
        }
        
        result = await persistence.save_session(session_id, context)
        
        assert result["success"] == True
        assert result["session_id"] == session_id
        assert "saved_at" in result
    
    @pytest.mark.asyncio
    async def test_load_session_context(self, persistence):
        """测试加载会话上下文"""
        session_id = "test_session_002"
        context = {"test": "data", "timestamp": "2026-02-13"}
        
        # 先保存
        await persistence.save_session(session_id, context)
        
        # 然后加载 - 使用直接SQL查询验证
        cursor = await persistence.initialize() or True
        
        import sqlite3
        conn = sqlite3.connect(persistence.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM sessions WHERE id = ?', (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        loaded_data = json.loads(result[0])
        assert loaded_data["test"] == "data"
    
    @pytest.mark.asyncio
    async def test_session_update(self, persistence):
        """测试会话更新"""
        session_id = "test_session_003"
        
        # 初始保存
        await persistence.save_session(session_id, {"version": 1})
        
        # 更新
        result = await persistence.save_session(session_id, {"version": 2})
        
        assert result["success"] == True
        
        # 验证更新成功
        import sqlite3
        conn = sqlite3.connect(persistence.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM sessions WHERE id = ?', (session_id,))
        result = cursor.fetchone()
        conn.close()
        
        assert json.loads(result[0])["version"] == 2
    
    @pytest.mark.asyncio
    async def test_versioning(self, versioning):
        """测试版本控制"""
        entity_type = "session"
        entity_id = "test_version_session"
        data = {"content": "version 1"}
        
        # 创建版本1
        v1 = await versioning.create_version(entity_type, entity_id, data)
        assert v1["version"] == 1
        
        # 创建版本2
        v2 = await versioning.create_version(entity_type, entity_id, {"content": "version 2"})
        assert v2["version"] == 2
        
        # 获取最新版本
        latest = await versioning.get_version(entity_type, entity_id)
        assert latest["version"] == 2
        assert latest["data"]["content"] == "version 2"
        
        # 获取版本历史
        history = await versioning.get_version_history(entity_type, entity_id)
        assert len(history) == 2
    
    @pytest.mark.asyncio
    async def test_version_revert(self, versioning):
        """测试版本回滚"""
        entity_type = "session"
        entity_id = "test_revert_session"
        
        # 创建版本
        await versioning.create_version(entity_type, entity_id, {"content": "v1"})
        await versioning.create_version(entity_type, entity_id, {"content": "v2"})
        
        # 回滚到版本1
        result = await versioning.revert_to_version(entity_type, entity_id, 1)
        
        assert result["success"] == True
        assert result["reverted_to_version"] == 1
        
        # 验证当前版本是回滚后的新版本（v3）
        latest = await versioning.get_version(entity_type, entity_id)
        assert latest["data"]["content"] == "v1"
        assert latest["version"] == 3
