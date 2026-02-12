# 🧠 Symbiosis Memory System V3 - 共生记忆系统 V3

**版本**: v3.0  
**状态**: ✅ 守护模式已激活 | 🔄 永久运行中

---

## 🎯 系统目标

Mac大白的**跨会话记忆系统**，实现真正的"共生"：

1. **跨会话记忆** - 新会话自动加载之前所有对话，不会"失忆"
2. **智能融合** - 自动把历史记忆注入到新会话上下文中
3. **每日自动压缩** - 每天0点自动压缩当天对话，生成智能摘要
4. **实时追踪** - 记录所有会话状态、版本、历史变更
5. **持久化存储** - SQLite数据库+文件双备份，数据永不丢失
6. **一键恢复** - 系统损坏后可从备份快速恢复

---

## 🛡️ 守护模式

### 功能特性

| 模式 | 状态 | 说明 |
|------|------|------|
| 永久记忆模式 | ✅ | SQLite持久化 + 实时写入 |
| 程序监控模式 | ✅ | 每10秒健康检查 |
| 守护模式 | ✅ | 崩溃自动重启 |
| 崩溃自动重启 | ✅ | 最多10次重启尝试 |
| 开机自动启动 | ✅ | Launchd服务 |
| Gateway同步启动 | ✅ | 监听OpenClaw启动 |

### 守护进程架构

```
┌─────────────────────────────────────────────┐
│         共生记忆系统 V3 守护架构              │
├─────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐│
│  │  launchd (开机自启)                      ││
│  │  └─→ monitor.sh (进程监控)               ││
│  │      └─→ daemon.py (守护进程)            ││
│  │          └─→ SymbiosisMemory (核心)       ││
│  │                                           ││
│  └─────────────────────────────────────────┘│
│                                             │
│  ┌─────────────────────────────────────────┐│
│  │  OpenClaw Gateway 同步                   ││
│  │  symbiosis-openclaw-sync.sh              ││
│  │  └─→ 自动跟随Gateway启动                 ││
│  └─────────────────────────────────────────┘│
│                                             │
│  ┌─────────────────────────────────────────┐│
│  │  数据层                                  ││
│  │  - SQLite (memory.db)                   ││
│  │  - 实时备份 (backups/)                  ││
│  │  - 日志 (symbiosis-*.log)               ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

---

## 🚀 快速启动

### 方式1：启动守护模式（推荐）
```bash
cd symbiosis-memory-system

# 方式1a：直接启动守护进程
bash start-daemon.sh

# 方式1b：启动完整监控（推荐）
bash monitor.sh start

# 方式1c：同时启动OpenClaw同步
bash symbiosis-openclaw-sync.sh start
```

### 方式2：安装开机自启
```bash
# 复制Launchd服务到用户Library
cp com.symbiosis.memory.v3.plist ~/Library/LaunchAgents/

# 加载服务
launchctl load ~/Library/LaunchAgents/com.symbiosis.memory.v3.plist

# 启动服务
launchctl start com.symbiosis.memory.v3

# 验证状态
launchctl list | grep symbiosis
```

### 方式3：手动启动核心
```bash
python3 main.py
```

---

## 📊 管理命令

### 守护进程管理
```bash
# 查看状态
bash monitor.sh status

# 停止
bash monitor.sh stop

# 重启
bash monitor.sh restart

# 查看日志
tail -f symbiosis-daemon.log
```

### OpenClaw同步管理
```bash
# 启动同步
bash symbiosis-openclaw-sync.sh start

# 查看同步状态
bash symbiosis-openclaw-sync.sh status

# 停止同步
bash symbiosis-openclaw-sync.sh stop
```

### 手动操作
```bash
# 启动守护进程
python3 daemon.py

# 测试保存功能
python3 run_v3.py

# 运行测试
python3 -m pytest tests/ -v
```

---

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `daemon.py` | 守护进程核心 |
| `start-daemon.sh` | 守护模式启动脚本 |
| `monitor.sh` | 进程监控脚本 |
| `symbiosis-openclaw-sync.sh` | OpenClaw同步脚本 |
| `main.py` | 系统主入口 |
| `run_v3.py` | 测试运行脚本 |
| `symbiosis.conf` | 配置文件 |
| `memory.db` | SQLite数据库 |
| `symbiosis-*.log` | 日志文件 |
| `backups/` | 自动备份目录 |
| `com.symbiosis.memory.v3.plist` | Launchd服务配置 |

---

## 🔧 配置说明

### symbiosis.conf
```ini
[守护模式]
enabled = true
max_restarts = 10
restart_interval = 5

[监控模式]
enabled = true
check_interval = 10
```

---

## 📈 测试结果

```
============================== 22 passed in 0.56s ==============================
✅ 会话管理测试
✅ 版本控制测试
✅ 每日日志测试
✅ 长期记忆测试
✅ 备份服务测试
✅ 持久化测试
✅ 完整流程测试
```

---

## 🎉 里程碑

| 日期 | 事件 |
|------|------|
| 2026-02-12 | 🎉 V3 开发启动 |
| 2026-02-12 18:49 | 🎤 语音系统首次完整播报 |
| 2026-02-12 22:00 | 🧠 V3 核心模块完成 |
| 2026-02-13 00:00 | 📦 每日压缩脚本完成 |
| 2026-02-13 03:00 | 🛡️ 备份恢复系统完成 |
| 2026-02-13 03:54 | ✅ V3 完整验证测试通过 |
| 2026-02-13 04:13 | 🛡️ 守护模式激活 |

---

## 🔄 永久运行状态

### 当前运行模式
- ✅ 守护进程: 活跃
- ✅ 进程监控: 活跃
- ✅ 崩溃重启: 启用
- ✅ 开机自启: 待配置
- ✅ OpenClaw同步: 待启动

### 日志位置
- 守护日志: `symbiosis-daemon.log`
- 监控日志: `symbiosis-monitor.log`
- 同步日志: `symbiosis-openclaw-sync.log`
- 错误日志: `symbiosis-launchd.error.log`

---

## ⚠️ 故障排除

### 进程未运行
```bash
bash monitor.sh status  # 检查状态
bash monitor.sh restart  # 重启
```

### 数据库损坏
```bash
# 检查完整性
sqlite3 memory.db "PRAGMA integrity_check;"

# 从备份恢复
ls backups/
cp backups/backup_xxx.db memory.db
```

### 重启次数过多
```bash
# 查看日志
tail -50 symbiosis-monitor.log

# 清理日志
> symbiosis-monitor.log
```

---

## 📚 相关文档

- [SPEC.md](SPEC.md) - 详细需求规格
- [PLAN.md](PLAN.md) - 技术方案

---

**维护者**: Mac大白 🦾  
**共生计划**: Project Symbiosis

> "从今天起，我再也不会忘记任何事情。"
