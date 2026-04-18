#!/usr/bin/env bash
# stop_mac.sh — 停止 M4 Mac 上所有 Kunomi 服務
set -eu
set -o pipefail 2>/dev/null || true

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }

stop_pid() {
    local name=$1
    local pidfile="logs/$2.pid"
    if [ -f "$pidfile" ]; then
        local pid
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            info "${name} stopped (PID: ${pid})"
        else
            warn "${name} not running (PID: ${pid})"
        fi
        rm -f "$pidfile"
    else
        warn "${name} PID file not found: ${pidfile}"
    fi
}

stop_pid "API 服務" "api"
stop_pid "Discord Bot" "discord"

info "所有服務已停止"
