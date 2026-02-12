# Tests - Full Integration Flow
import pytest
import json
import os
import sys
import tempfile
import asyncio
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database import DatabaseCore
from main import SymbiosisMemory


@pytest.fixture
async def system():
    """创建完整的共生记忆系统"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    sys = SymbiosisMemory(db_path=path)
    await sys.initialize()
    
    yield sys
    
    await sys.close()
    os.unlink(path)


@pytest.mark.asyncio
async def test_complete_session_flow(system):
    """测试完整的会话流程"""
    # 1. 保存会话
    result = await system.save_session_context(
        'session_001',
        {'message': '测试会话', 'step': 1}
    )
    assert result['success'] is True
    
    # 2. 加载会话
    context = await system.load_session_context('session_001')
    assert context is not None
    assert context['message'] == '测试会话'
    
    # 3. 更新会话
    result2 = await system.save_session_context(
        'session_001',
        {'message': '更新后的会话', 'step': 2}
    )
    assert result2['version'] == 2


@pytest.mark.asyncio
async def test_version_history_trace(system):
    """测试版本历史追溯"""
    # 创建多个版本
    for i in range(3):
        await system.save_session_context(
            'version_test',
            {'version': i+1, 'data': f'数据{i}'}
        )
    
    # 获取版本历史 - 使用versioning服务
    history = await system.versioning.get_version_history('session', 'version_test')
    assert len(history) >= 3


@pytest.mark.asyncio
async def test_daily_log_integration(system):
    """测试每日日志集成"""
    await system.daily_log.append_entry(
        entry='集成测试',
        category='test'
    )
    
    logs = await system.daily_log.get_entries()
    assert logs is not None
