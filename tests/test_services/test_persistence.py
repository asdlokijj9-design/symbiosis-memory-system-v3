# Tests - Persistence Service
import pytest
import json
import os
import sys
import tempfile
import asyncio
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database import DatabaseCore
from services.persistence_service import PersistenceService


@pytest.fixture
async def db():
    """创建临时数据库"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    database = DatabaseCore(path)
    await database.initialize()
    
    yield database
    
    await database.close()
    os.unlink(path)


@pytest.fixture
def persistence(db):
    """创建持久化服务"""
    return PersistenceService(db.db_path)


@pytest.mark.asyncio
async def test_save_immediately(persistence):
    """测试立即保存"""
    result = await persistence.save_session(
        'test_session_001',
        {'message': '测试数据'}
    )
    assert result['success'] is True


@pytest.mark.asyncio
async def test_get_all_sessions(persistence):
    """测试获取所有会话"""
    await persistence.save_session('session_1', {'data': 1})
    await persistence.save_session('session_2', {'data': 2})
    
    sessions = await persistence.get_all_sessions()
    assert len(sessions) >= 2


@pytest.mark.asyncio
async def test_bulk_save(persistence):
    """测试批量保存"""
    sessions = [
        ('bulk_1', {'item': 1}),
        ('bulk_2', {'item': 2}),
        ('bulk_3', {'item': 3})
    ]
    
    for session_id, data in sessions:
        await persistence.save_session(session_id, data)
    
    all_sessions = await persistence.get_all_sessions()
    assert len(all_sessions) >= 3
