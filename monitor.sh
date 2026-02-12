#!/bin/bash
# 共生记忆系统 V3 - 进程监控脚本
# 功能：
# - 检查进程是否存活
# - 自动重启崩溃的进程
# - 记录监控日志
# - 开机自启

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="$SCRIPT_DIR/symbiosis-monitor.log"
PID_FILE="$SCRIPT_DIR/symbiosis-daemon.pid"
DAEMON_SCRIPT="$SCRIPT_DIR/start-daemon.sh"
MAX_RESTARTS=5
RESTART_WINDOW=60  # 60秒内最多重启5次

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_process() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            return 0  # 进程存活
        fi
    fi
    return 1  # 进程不存在
}

get_restart_count() {
    # 获取60秒内的重启次数
    if [ -f "$LOG_FILE" ]; then
        tail -100 "$LOG_FILE" | grep -c "🚀 守护进程已启动" 2>/dev/null || echo 0
    else
        echo 0
    fi
}

restart_daemon() {
    local restarts=$(get_restart_count)
    
    if [ "$restarts" -ge "$MAX_RESTARTS" ]; then
        log "❌ 崩溃次数过多 ($restarts/$MAX_RESTARTS)，等待冷却..."
        sleep 30
    fi
    
    log "🔄 尝试重启守护进程..."
    
    # 清理旧进程
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 $OLD_PID 2>/dev/null; then
            kill $OLD_PID 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi
    
    # 启动守护进程
    cd "$SCRIPT_DIR"
    nohup bash "$DAEMON_SCRIPT" >> "$LOG_FILE" 2>&1 &
    
    sleep 2
    
    if check_process; then
        log "✅ 重启成功"
    else
        log "❌ 重启失败"
    fi
}

monitor_loop() {
    log "========================================"
    log "🧠 共生记忆系统 V3 - 监控启动"
    log "📅 $(date '+%Y-%m-%d %H:%M:%S')"
    log "========================================"
    
    while true; do
        if check_process; then
            log "✅ 进程运行正常"
        else
            log "⚠️ 进程未运行，尝试启动..."
            restart_daemon
        fi
        
        # 检查间隔
        sleep 10
    done
}

# 主逻辑
case "$1" in
    start)
        monitor_loop &
        echo "✅ 监控已启动 (后台运行)"
        echo "📝 日志: $LOG_FILE"
        ;;
    stop)
        log "🛑 停止监控..."
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            kill $PID 2>/dev/null || true
            rm -f "$PID_FILE"
        fi
        pkill -f "symbiosis-monitor.sh" 2>/dev/null || true
        echo "✅ 监控已停止"
        ;;
    status)
        if check_process; then
            echo "✅ 共生记忆系统运行中"
            PID=$(cat "$PID_FILE")
            echo "PID: $PID"
            ps -p $PID -o pid,ppid,cmd,etime
        else
            echo "❌ 共生记忆系统未运行"
        fi
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    *)
        echo "用法: $0 {start|stop|status|restart}"
        echo ""
        echo "命令:"
        echo "  start   - 启动监控（后台）"
        echo "  stop    - 停止监控"
        echo "  status  - 查看状态"
        echo "  restart - 重启监控"
        exit 1
        ;;
esac
