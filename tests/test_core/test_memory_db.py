# Tests - Memory Database Core
import pytest
import json
import os
import sys
import tempfile
import asyncio
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database import DatabaseCore


@pytest.fixture
async def db():
    """创建临时数据库实例"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    database = DatabaseCore(path)
    await database.initialize()
    
    yield database
    
    # 清理
    await database.close()
    if os.path.exists(path):
        os.unlink(path)


@pytest.mark.asyncio
async def test_create_tables(db):
    """测试表创建"""
    # 验证表存在
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor]
    assert 'sessions' in tables
    assert 'memory' in tables
    assert 'daily_logs' in tables
    assert 'versions' in tables


@pytest.mark.asyncio
async def test_save_and_get_memory(db):
    """测试保存和获取记忆"""
    # 保存会话
    session_id = "test_session_001"
    content = json.dumps({"message": "Hello World"})
    now = datetime.now().isoformat()
    
    await db.execute(
        'INSERT INTO sessions (id, created_at, updated_at, data) VALUES (?, ?, ?, ?)',
        (session_id, now, now, content)
    )
    
    # 获取 - execute返回fetchall()结果列表
    cursor = await db.execute('SELECT data FROM sessions WHERE id = ?', (session_id,))
    results = cursor  # cursor已经是fetchall()的结果
    assert len(results) > 0, "查询结果为空"
    assert json.loads(results[0][0])['message'] == "Hello World"


@pytest.mark.asyncio
async def test_version_history(db):
    """测试版本历史"""
    entity_type = "test_entity"
    entity_id = "test_id"
    
    # 创建多个版本
    for i in range(3):
        await db.execute(
            'INSERT INTO versions (entity_type, entity_id, version, data, created_at) VALUES (?, ?, ?, ?, ?)',
            (entity_type, entity_id, i+1, json.dumps({"version": i+1}), datetime.now().isoformat())
        )
    
    # 获取版本历史
    cursor = await db.execute(
        'SELECT version FROM versions WHERE entity_type = ? AND entity_id = ? ORDER BY version',
        (entity_type, entity_id)
    )
    versions = [r[0] for r in cursor]
    assert versions == [1, 2, 3]


@pytest.mark.asyncio
async def test_concurrent_write_simulation(db):
    """测试并发写入"""
    results = []
    
    for i in range(5):
        session_id = f"session_{i}"
        now = datetime.now().isoformat()
        await db.execute(
            'INSERT INTO sessions (id, created_at, updated_at, data) VALUES (?, ?, ?, ?)',
            (session_id, now, now, json.dumps({"thread": i}))
        )
        results.append(session_id)
    
    # 验证所有写入都成功
    assert len(results) == 5
    
    # 验证数据
    cursor = await db.execute('SELECT COUNT(*) FROM sessions')
    assert cursor[0][0] == 5
