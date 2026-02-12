# Tests - Daily Logger & Longterm Memory
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
from modules.daily_log import DailyLogModule
from modules.longterm_memory import LongtermMemoryModule


@pytest.fixture
async def db():
    """创建临时数据库"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    database = DatabaseCore(path)
    await database.initialize()
    
    yield database
    
    # 清理
    await database.close()
    os.unlink(path)


@pytest.fixture
def daily_logger(db):
    """创建每日日志记录器"""
    import tempfile
    log_dir = tempfile.mkdtemp()
    return DailyLogModule(log_dir=log_dir)


@pytest.fixture
def longterm_memory(db):
    """创建长期记忆模块"""
    import tempfile
    fd, mem_path = tempfile.mkstemp(suffix='.md')
    os.close(fd)
    return LongtermMemoryModule(memory_path=mem_path)


class TestDailyLogger:
    """测试每日日志管理器"""
    
    @pytest.mark.asyncio
    async def test_append_entry(self, daily_logger):
        """测试记录每日事件"""
        event_id = await daily_logger.append_entry(
            entry='测试事件',
            category='test'
        )
        assert event_id is not None
    
    @pytest.mark.asyncio
    async def test_get_entries(self, daily_logger):
        """测试获取日志"""
        # 先记录一些事件
        await daily_logger.append_entry(entry='事件1', category='test')
        await daily_logger.append_entry(entry='事件2', category='test')
        
        # 获取日志
        logs = await daily_logger.get_entries()
        assert logs is not None
        assert len(logs) >= 2


class TestLongtermMemory:
    """测试长期记忆模块"""
    
    @pytest.mark.asyncio
    async def test_add_memory(self, longterm_memory):
        """测试保存长期记忆"""
        mem_id = await longterm_memory.add_memory(
            category='test',
            content='这是一条测试记忆',
            priority=5
        )
        assert mem_id is not None
    
    @pytest.mark.asyncio
    async def test_add_multiple_memories(self, longterm_memory):
        """测试保存多条记忆"""
        result1 = await longterm_memory.add_memory(category='tech', content='关于AI的记忆', priority=8)
        result2 = await longterm_memory.add_memory(category='business', content='关于电商的记忆', priority=6)
        
        # 验证都成功保存
        assert result1 is not None
        assert result2 is not None
