# Tests - Backup Service
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
from services.backup_service import BackupService


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
def backup_service(db):
    """创建备份服务"""
    backup_dir = tempfile.mkdtemp()
    return BackupService(db.db_path, backup_dir=backup_dir)


@pytest.mark.asyncio
async def test_create_backup(backup_service):
    """测试创建备份"""
    result = await backup_service.create_backup()
    assert result['success'] is True
    assert 'backup_path' in result


@pytest.mark.asyncio
async def test_list_backups(backup_service):
    """测试列出备份"""
    await backup_service.create_backup()
    backups = await backup_service.list_backups()
    assert len(backups) >= 1


@pytest.mark.asyncio
async def test_backup_file_naming(backup_service):
    """测试备份文件命名"""
    result = await backup_service.create_backup()
    assert '.db' in result['backup_path']
