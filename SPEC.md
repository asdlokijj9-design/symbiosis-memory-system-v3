# Local Memory System V3 - SPEC.md

## 项目概述
构建一个"永远不出错"的永久记忆系统，提供跨会话记忆、每日日志、长期记忆、版本追溯、实时持久化和本地备份功能。

---

## 功能点清单

### 1. 跨会话记忆（Session Context）
- 自动保存当前会话上下文到 `.session_context.txt`
- 新会话启动时自动加载历史上下文
- 支持会话历史记录和追溯

### 2. 每日日志（Daily Logs）
- 自动按日期创建 `memory/YYYY-MM-DD.md`
- 记录每日发生的所有重要事件
- 支持按日期查询历史日志

### 3. 长期记忆（Permanent Memory）
- 自动从每日日志中提取重要信息
- 沉淀到 `MEMORY.md` 长期记忆库
- 支持重要事件的标记和归档

### 4. 版本化存储（Versioning）
- SQLite 数据库存储所有数据
- 每次修改保留完整历史版本
- 支持查看任意时间点的记忆状态

### 5. 冲突解决（Conflict Resolution）
- 保留所有版本（不覆盖）
- 新旧记忆同时存在
- 支持版本对比和融合

### 6. 实时持久化（Real-time Persistence）
- 每次对话后立即写入数据库
- 内存缓存 + 定时刷盘（双保险）
- 崩溃恢复机制

### 7. 自动提取（Auto Extraction）
- 自动识别日志中的重要信息
- 定时提取并归档到长期记忆
- 支持手动触发提取

### 8. 本地备份（Local Backup）
- 定时自动备份到本地副本
- 支持手动备份和恢复
- 备份版本管理

### 9. 记忆融合（Memory Fusion）
- 新旧记忆系统无缝融合
- `.session_context.txt` + daily logs + MEMORY.md 统一管理
- 智能合并冲突内容

---

## 输入输出示例

### 输入
```python
# 保存会话上下文
memory_system.save_session_context({
    "session_id": "session_001",
    "user_message": "记得上次回话内容吗",
    "assistant_response": "当然记得！2026-02-12..."
})
```

### 输出
```json
{
    "id": 1,
    "session_id": "session_001",
    "content": {
        "user_message": "记得上次回话内容吗",
        "assistant_response": "当然记得！2026-02-12..."
    },
    "timestamp": "2026-02-13T02:50:00",
    "version": 1
}
```

---

## 边界条件

| 条件 | 处理方式 |
|------|---------|
| 数据库文件损坏 | 自动从备份恢复；若无可用备份，重建空数据库并记录错误 |
| 磁盘空间不足 | 警告+拒绝写入，保留只读模式 |
| 并发写入冲突 | SQLite 事务锁，自动重试 3 次 |
| 内存缓存溢出 | LRU 淘汰策略，最大缓存 1000 条 |
| 日期格式错误 | 抛出 ValidationError，提示正确的 YYYY-MM-DD 格式 |
| 空内容写入 | 拒绝并记录警告，防止空记录污染数据库 |

---

## 错误处理清单

| 错误类型 | 处理方式 | 恢复策略 |
|---------|---------|---------|
| DatabaseError | 回滚事务，记录错误，重试 | 最多重试 3 次，指数退避 |
| DiskFullError | 拒绝写入，发送告警 | 人工清理磁盘空间后恢复 |
| MemoryOverflow | LRU 淘汰旧缓存，强制刷盘 | 继续服务，记录警告 |
| ConcurrentWriteError | SQLite 锁等待，超时后报错 | 自动重试，通知用户 |
| CorruptedBackupError | 标记备份无效，使用上一版本 | 告警，提示手动检查 |
| ValidationError | 拒绝写入，返回错误详情 | 不写入，记录错误 |

---

## 目录结构

```
~/workspace/local-memory-system-v3/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── memory_db.py          # SQLite 数据库核心
│   │   ├── session_manager.py    # 会话上下文管理
│   │   ├── daily_logger.py       # 每日日志管理
│   │   └── longterm_memory.py    # 长期记忆管理
│   ├── services/
│   │   ├── __init__.py
│   │   ├── versioning.py         # 版本化服务
│   │   ├── persistence.py        # 实时持久化服务
│   │   ├── backup.py             # 本地备份服务
│   │   └── fusion.py             # 记忆融合服务
│   └── utils/
│       ├── __init__.py
│       └── helpers.py            # 工具函数
├── tests/
│   ├── __init__.py
│   ├── test_core/
│   ├── test_services/
│   └── test_integration/
├── data/
│   ├── memory.db                 # SQLite 数据库文件
│   └── backups/                  # 备份目录
├── SPEC.md
├── PLAN.md
├── requirements.txt
└── README.md
```

---

## 验证命令

```bash
# 运行所有测试
pytest -q tests/

# 运行特定模块测试
pytest -q tests/test_core/
pytest -q tests/test_services/

# 数据库完整性检查
python -m src.core.memory_db --check-integrity

# 备份恢复测试
python -m src.services.backup --test-restore
```

---

## 性能要求

- **写入延迟**: < 10ms（单条记录）
- **查询延迟**: < 50ms（常规查询）
- **并发支持**: 最多 10 个并发连接
- **磁盘空间**: 每天约 10KB（按每天 100 条对话估算）
- **启动时间**: < 500ms（冷启动）

---

## 可靠性要求

- **数据完整性**: 100%（每次写入都持久化）
- **崩溃恢复**: 自动恢复到最近一次成功状态
- **备份频率**: 每小时自动备份 + 每次重要操作后备份
- **版本保留**: 永久保留所有版本（支持历史追溯）

---

最后更新: 2026-02-13 02:50
