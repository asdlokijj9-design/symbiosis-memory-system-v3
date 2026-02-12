#!/bin/bash
# 共生记忆系统 V3 - OpenClaw Gateway 同步启动脚本
# 功能：
# - 监听 OpenClaw Gateway 启动事件
# - 自动同步启动共生记忆系统
# - 处理进程依赖关系

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="$SCRIPT_DIR/symbiosis-openclaw-sync.log"
DAEMON_SCRIPT="$SCRIPT_DIR/start-daemon.sh"
MONITOR_SCRIPT="$SCRIPT_DIR/monitor.sh"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_openclaw_gateway() {
    # 检查OpenClaw Gateway进程
    if pgrep -f "openclaw" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

check_symbiosis_running() {
    # 检查共生记忆是否已运行
    if pgrep -f "python3.*daemon.py" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

sync_start() {
    log "========================================"
    log "🔗 OpenClaw Gateway 同步启动"
    log "📅 $(date '+%Y-%m-%d %H:%M:%S')"
    log "========================================"
    
    while true; do
        # 检查OpenClaw是否运行
        if check_openclaw_gateway; then
            if ! check_symbiosis_running; then
                log "🚀 OpenClaw已启动，启动共生记忆系统..."
                bash "$MONITOR_SCRIPT" start
                log "✅ 共生记忆系统已启动"
            else
                log "✅ 共生记忆系统已在运行"
            fi
        else
            log "⚠️ OpenClaw未运行，等待..."
        fi
        
        # 检查间隔
        sleep 5
    done
}

# 主逻辑
case "$1" in
    start)
        sync_start &
        echo "✅ 同步启动已激活 (后台运行)"
        echo "📝 日志: $LOG_FILE"
        ;;
    stop)
        log "🛑 停止同步..."
        pkill -f "symbiosis-openclaw-sync.sh" 2>/dev/null || true
        echo "✅ 同步已停止"
        ;;
    status)
        echo "🔗 OpenClaw 同步状态:"
        if pgrep -f "symbiosis-openclaw-sync.sh" > /dev/null 2>&1; then
            echo "✅ 同步脚本运行中"
        else
            echo "❌ 同步脚本未运行"
        fi
        echo ""
        echo "🔄 OpenClaw Gateway:"
        if check_openclaw_gateway; then
            echo "✅ OpenClaw运行中"
        else
            echo "❌ OpenClaw未运行"
        fi
        echo ""
        echo "🧠 共生记忆系统:"
        if check_symbiosis_running; then
            echo "✅ 共生记忆运行中"
        else
            echo "❌ 共生记忆未运行"
        fi
        ;;
    *)
        echo "用法: $0 {start|stop|status}"
        echo ""
        echo "命令:"
        echo "  start   - 启动同步（后台）"
        echo "  stop    - 停止同步"
        echo "  status  - 查看状态"
        exit 1
        ;;
esac
