"""
共生记忆系统直接启动脚本

解决相对导入问题，直接在共生记忆目录下运行

使用方法:
    cd symbiosis-memory-system
    python3 run.py
"""

import sys
import os
from pathlib import Path

# 确保共生记忆目录在路径中
SYSTEM_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SYSTEM_DIR))

import asyncio
from main import SymbiosisMemory


async def test_save():
    """测试保存功能"""
    system = SymbiosisMemory(db_path=str(SYSTEM_DIR / "memory.db"))
    await system.initialize()
    
    from datetime import datetime
    
    result = await system.save_session_context(
        "symbiosis_direct_test",
        {
            "summary": "共生记忆系统直接测试保存功能",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    print(f"✅ 保存成功: v{result['version']}")
    
    # 验证
    loaded = await system.load_session_context("symbiosis_direct_test")
    print(f"✅ 加载成功: {loaded['summary']}")
    
    # 检查数据库
    import sqlite3
    conn = sqlite3.connect(str(SYSTEM_DIR / "memory.db"))
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM sessions')
    sessions = cursor.fetchall()
    print(f"✅ 数据库会话数: {len(sessions)}")
    conn.close()
    
    await system.close()


if __name__ == "__main__":
    asyncio.run(test_save())
