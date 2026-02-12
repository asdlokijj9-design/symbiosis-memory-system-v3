#!/usr/bin/env python3
"""
共生记忆系统 V3 - 守护进程
功能：
- 崩溃自动重启
- 程序健康监控
- 日志记录
- 优雅关闭
"""

import os
import sys
import signal
import asyncio
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# 配置日志
LOG_FILE = Path(__file__).parent / "symbiosis-daemon.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SymbiosisDaemon:
    """共生记忆守护进程"""
    
    def __init__(self):
        self.running = False
        self.system = None
        self.restart_count = 0
        self.max_restarts = 10  # 最多重启10次
        self.restart_interval = 5  # 重启间隔5秒
        
    async def start_system(self) -> bool:
        """启动共生记忆系统"""
        try:
            from main import SymbiosisMemory
            
            logger.info("🚀 启动共生记忆系统...")
            # Set SYMBIOSIS_DB_PATH for daemon
            os.environ['SYMBIOSIS_DB_PATH'] = r"/Users/imac/.openclaw/workspace/symbiosis-memory-system/memory.db"
            self.system = SymbiosisMemory()
            # Force daemon to use on-disk DB instead of ':memory:'
            if hasattr(self.system, 'persistence') and self.system.persistence:
                self.system.persistence.db_path = r"/Users/imac/.openclaw/workspace/symbiosis-memory-system/memory.db"
            
            await self.system.initialize()
            logger.info(f"📂 DB路径: {getattr(self.system.persistence, 'db_path', '(unknown)')}")
            logger.info("✅ 共生记忆系统启动成功")
            return True
            
        except Exception as e:
            logger.error("❌ 启动失败: " + str(e))
            return False
    
    async def check_health(self) -> bool:
        """健康检查"""
        try:
            if not self.system:
                return False
            
            # 检查数据库连接 - 尝试查询
            if hasattr(self.system, 'persistence'):
                await self.system.persistence.get_all_sessions(limit=1)
            return True
            
        except Exception as e:
            logger.error("健康检查失败: " + str(e))
            return False
    
    async def run(self):
        """主运行循环"""
        self.running = True
        
        while self.running:
            # 启动系统
            if not await self.start_system():
                await self.handle_crash()
                continue
            
            self.restart_count = 0
            
            # 主循环 - 监控健康状态
            while self.running:
                await asyncio.sleep(30)  # 每30秒检查一次
                
                if not await self.check_health():
                    logger.warning("⚠️ 健康检查失败，尝试恢复...")
                    await self.system.close()
                    await asyncio.sleep(5)
                    break
        
        # 优雅关闭
        await self.shutdown()
    
    async def handle_crash(self):
        """处理崩溃"""
        self.restart_count += 1
        
        if self.restart_count > self.max_restarts:
            logger.critical(f"❌ 崩溃次数过多 ({self.restart_count})，停止重启")
            self.running = False
            return
        
        logger.info(f"🔄 崩溃重启 {self.restart_count}/{self.max_restarts}")
        await asyncio.sleep(self.restart_interval)
    
    async def shutdown(self):
        """优雅关闭"""
        logger.info("🛑 关闭共生记忆系统...")
        try:
            if self.system:
                await self.system.close()
            logger.info("✅ 关闭完成")
        except Exception as e:
            logger.error(f"关闭失败: {e}")
        
        sys.exit(0)
    
    def stop(self):
        """停止守护进程"""
        logger.info("🛑 收到停止信号")
        self.running = False

async def main():
    """主入口"""
    daemon = SymbiosisDaemon()
    
    # 信号处理
    def handle_signal(signum, frame):
        logger.info(f"📡 收到信号 {signum}")
        daemon.stop()
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # 记录启动时间
    logger.info("=" * 60)
    logger.info("🧠 共生记忆系统 V3 守护进程启动")
    logger.info(f"📅 启动时间: {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    await daemon.run()

if __name__ == "__main__":
    asyncio.run(main())
