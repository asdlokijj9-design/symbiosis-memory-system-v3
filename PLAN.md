# Local Memory System V3 - PLAN.md

## 数据库设计

### 主表：memories（记忆表）
```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_type TEXT NOT NULL,           -- 'session' | 'daily' | 'longterm'
    session_id TEXT,                      -- 会话ID（可选）
    date TEXT,                            -- 日期（YYYY-MM-DD）
    content TEXT NOT NULL,                -- JSON 内容
    importance INTEGER DEFAULT 0,         -- 重要性评分 0-10
    tags TEXT,                            -- 标签（逗号分隔）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER DEFAULT 0
);
```

### 表：versions（版本历史表）
```sql
CREATE TABLE versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER REFERENCES memories(id),
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    changed_by TEXT,                      -- 'user' | 'auto_extraction' | 'fusion'
    change_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 表：backups（备份记录表）
```sql
CREATE TABLE backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_type TEXT NOT NULL,            -- 'scheduled' | 'manual' | 'auto'
    file_path TEXT NOT NULL,
    size_bytes INTEGER,
    checksum TEXT,
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 索引优化
```sql
CREATE INDEX idx_memories_type ON memories(memory_type);
CREATE INDEX idx_memories_session ON memories(session_id);
CREATE INDEX idx_memories_date ON memories(date);
CREATE INDEX idx_versions_memory ON versions(memory_id);
```

---

## 核心模块函数签名

### memory_db.py
```python
class MemoryDB:
    """SQLite 数据库核心类"""
    
    def __init__(self, db_path: str = "data/memory.db"):
        """初始化数据库连接"""
    
    def create_tables(self) -> None:
        """创建所有表（如果不存在）"""
    
    def save_memory(
        self,
        memory_type: str,
        session_id: Optional[str] = None,
        date: Optional[str] = None,
        content: Dict,
        importance: int = 0,
        tags: Optional[List[str]] = None
    ) -> int:
        """保存记忆，返回记忆ID"""
    
    def get_memory(self, memory_id: int) -> Optional[Dict]:
        """获取单条记忆"""
    
    def get_memories(
        self,
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None,
        date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """查询记忆列表"""
    
    def update_memory(
        self,
        memory_id: int,
        content: Dict,
        changed_by: str = "user",
        change_reason: str = None
    ) -> bool:
        """更新记忆（自动创建新版本）"""
    
    def get_versions(self, memory_id: int) -> List[Dict]:
        """获取某条记忆的所有版本"""
    
    def restore_version(self, version_id: int) -> bool:
        """恢复到指定版本"""
    
    def create_backup(self, backup_type: str = "auto") -> int:
        """创建备份，返回备份ID"""
    
    def restore_backup(self, backup_id: int) -> bool:
        """从备份恢复"""
    
    def check_integrity(self) -> Dict:
        """检查数据库完整性"""
    
    def close(self) -> None:
        """关闭数据库连接"""
```

### session_manager.py
```python
class SessionManager:
    """会话上下文管理器"""
    
    def __init__(self, db: MemoryDB):
        """初始化"""
    
    def save_session_context(
        self,
        session_id: str,
        context: Dict,
        file_path: str = "~/.openclaw/workspace/.session_context.txt"
    ) -> bool:
        """保存会话上下文到数据库和文件"""
    
    def load_session_context(
        self,
        file_path: str = "~/.openclaw/workspace/.session_context.txt"
    ) -> Optional[Dict]:
        """加载会话上下文"""
    
    def get_session_history(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """获取会话历史"""
    
    def save_conversation(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str
    ) -> int:
        """保存单条对话记录"""
    
    def get_conversation_history(
        self,
        session_id: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """获取对话历史"""
```

### daily_logger.py
```python
class DailyLogger:
    """每日日志管理器"""
    
    def __init__(self, db: MemoryDB, log_dir: str = "memory"):
        """初始化"""
    
    def log_event(
        self,
        date: str,
        event_type: str,
        content: Dict,
        importance: int = 0
    ) -> int:
        """记录每日事件"""
    
    def get_daily_log(self, date: str) -> List[Dict]:
        """获取某天的日志"""
    
    def export_to_markdown(
        self,
        date: str,
        output_path: str = None
    ) -> str:
        """导出某天日志为 Markdown 格式"""
    
    def get_recent_events(
        self,
        days: int = 7,
        importance_threshold: int = 5
    ) -> List[Dict]:
        """获取最近的重要事件"""
```

### longterm_memory.py
```python
class LongtermMemory:
    """长期记忆管理器"""
    
    def __init__(self, db: MemoryDB):
        """初始化"""
    
    def extract_and_archive(
        self,
        daily_log_ids: List[int],
        destination: str = "MEMORY.md"
    ) -> int:
        """从每日日志中提取重要信息并归档"""
    
    def save_longterm_memory(
        self,
        content: Dict,
        importance: int = 8,
        tags: List[str] = None
    ) -> int:
        """直接保存长期记忆"""
    
    def search_memories(
        self,
        query: str,
        tags: List[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """搜索长期记忆"""
    
    def get_memory_graph(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> Dict:
        """获取记忆图谱（按时间/标签组织）"""
    
    def merge_memories(
        self,
        memory_ids: List[int],
        strategy: str = "keep_all"
    ) -> int:
        """合并多条记忆"""
```

### persistence.py
```python
class PersistenceService:
    """实时持久化服务"""
    
    def __init__(self, db: MemoryDB, flush_interval: float = 1.0):
        """初始化（flush_interval = 刷盘间隔秒数）"""
    
    def save_immediately(
        self,
        memory_type: str,
        content: Dict,
        **kwargs
    ) -> int:
        """立即保存（绕过缓存）"""
    
    def queue_save(
        self,
        memory_type: str,
        content: Dict,
        **kwargs
    ) -> bool:
        """加入保存队列（异步）"""
    
    def force_flush(self) -> int:
        """强制刷盘（清空缓存）"""
    
    def get_queue_size(self) -> int:
        """获取队列中待保存的数量"""
    
    def get_status(self) -> Dict:
        """获取服务状态"""
```

### backup.py
```python
class BackupService:
    """本地备份服务"""
    
    def __init__(self, db: MemoryDB, backup_dir: str = "data/backups"):
        """初始化"""
    
    def create_backup(
        self,
        backup_type: str = "auto",
        description: str = None
    ) -> int:
        """创建备份"""
    
    def restore_backup(self, backup_id: int) -> bool:
        """从备份恢复"""
    
    def list_backups(
        self,
        backup_type: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """列出备份"""
    
    def cleanup_old_backups(
        self,
        keep_count: int = 10
    ) -> int:
        """清理旧备份（保留最近 N 个）"""
    
    def verify_backup(self, backup_id: int) -> Dict:
        """验证备份完整性"""
```

### fusion.py
```python
class MemoryFusion:
    """记忆融合服务"""
    
    def __init__(self, db: MemoryDB):
        """初始化"""
    
    def fuse_session_context(
        self,
        session_context: Dict,
        existing_memories: List[Dict]
    ) -> Dict:
        """融合会话上下文与现有记忆"""
    
    def fuse_daily_with_longterm(
        self,
        daily_id: int,
        longterm_ids: List[int]
    ) -> List[int]:
        """融合每日日志与长期记忆"""
    
    def resolve_conflict(
        self,
        memories: List[Dict],
        strategy: str = "keep_all"
    ) -> Dict:
        """解决记忆冲突"""
    
    def export_fused_memory(
        self,
        output_path: str = "MEMORY.md"
    ) -> bool:
        """导出融合后的记忆到 MEMORY.md"""
```

---

## 依赖清单（requirements.txt）

```python
# Core
sqlite3  # Python 内置，无需安装

# Testing
pytest>=7.0.0
pytest-asyncio>=0.21.0

# Utilities
python-dateutil>=2.8.2
chardet>=5.0.0

# Optional（未来扩展）
# alembic>=1.10.0  # 数据库迁移
# APScheduler>=3.10.0  # 定时任务
```

---

## 执行步骤

### Step 1: 数据库核心层
```bash
# 创建目录结构
mkdir -p src/core src/services src/utils tests/test_core tests/test_services tests/test_integration data/backups

# 创建数据库核心模块
touch src/core/__init__.py src/core/memory_db.py
```

### Step 2: 会话管理模块
```bash
# 实现会话上下文管理
touch src/core/session_manager.py
```

### Step 3: 每日日志模块
```bash
# 实现每日日志功能
touch src/core/daily_logger.py
```

### Step 4: 长期记忆模块
```bash
# 实现长期记忆管理
touch src/core/longterm_memory.py
```

### Step 5: 服务层
```bash
# 实现版本化、持久化、备份、融合服务
touch src/services/versioning.py
touch src/services/persistence.py
touch src/services/backup.py
touch src/services/fusion.py
```

### Step 6: 测试层
```bash
# 创建测试用例
touch tests/__init__.py
touch tests/test_core/__init__.py
touch tests/test_core/test_memory_db.py
touch tests/test_core/test_session_manager.py
touch tests/test_core/test_daily_logger.py
touch tests/test_core/test_longterm_memory.py
touch tests/test_services/__init__.py
touch tests/test_services/test_versioning.py
touch tests/test_services/test_persistence.py
touch tests/test_services/test_backup.py
touch tests/test_services/test_fusion.py
touch tests/test_integration/__init__.py
touch tests/test_integration/test_full_flow.py
```

### Step 7: 集成测试
```bash
# 运行完整流程测试
pytest -q tests/test_integration/test_full_flow.py
```

---

## 错误码定义

| 错误码 | 说明 | 处理建议 |
|-------|------|---------|
| ERR001 | 数据库连接失败 | 检查 db_path 是否正确，文件是否损坏 |
| ERR002 | 写入冲突 | 等待锁释放，重试操作 |
| ERR003 | 内存溢出 | 清理缓存，强制刷盘 |
| ERR004 | 备份失败 | 检查备份目录权限，清理磁盘空间 |
| ERR005 | 版本不存在 | 检查 version_id 是否正确 |
| ERR006 | 验证失败 | 检查输入参数格式 |
| ERR007 | 磁盘空间不足 | 清理文件和旧备份 |

---

## 监控指标

| 指标 | 阈值 | 告警级别 |
|-----|------|---------|
| 写入延迟 | > 100ms | WARNING |
| 查询延迟 | > 500ms | WARNING |
| 队列积压 | > 1000 | CRITICAL |
| 磁盘使用率 | > 80% | WARNING |
| 备份失败 | 连续 3 次 | CRITICAL |

---

最后更新: 2026-02-13 02:51
