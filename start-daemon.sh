#!/bin/bash
# 共生记忆系统 V3 - 守护模式启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "🧠 共生记忆系统 V3 - 守护模式"
echo "========================================"
echo ""

# 检查是否已经在运行
if pgrep -f "python3.*daemon.py" > /dev/null 2>&1; then
    echo "⚠️ 守护进程已在运行中"
    echo ""
    echo "状态:"
    ps aux | grep "python3.*daemon.py" | grep -v grep
    exit 0
fi

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "⚠️ 未找到 requirements.txt"
fi

# 启动守护进程
echo "🚀 启动守护进程..."
echo ""

# 使用nohup后台运行
nohup python3 daemon.py >> symbiosis-daemon.log 2>&1 &

DAEMON_PID=$!
echo "✅ 守护进程已启动 (PID: $DAEMON_PID)"

# 等待1秒让进程启动
sleep 1

# 检查进程是否存活
if kill -0 $DAEMON_PID 2>/dev/null; then
    echo "✅ 进程状态: 运行中"
    echo ""
    echo "📊 监控命令:"
    echo "  - 查看日志: tail -f symbiosis-daemon.log"
    echo "  - 停止服务: pkill -f 'python3.*daemon.py'"
    echo "  - 检查状态: ps aux | grep daemon.py"
else
    echo "❌ 进程启动失败"
    echo ""
    echo "📝 查看日志:"
    tail -20 symbiosis-daemon.log
    exit 1
fi

# 保存PID
echo $DAEMON_PID > symbiosis-daemon.pid

echo ""
echo "========================================"
echo "🎉 守护模式已激活！"
echo "========================================"
