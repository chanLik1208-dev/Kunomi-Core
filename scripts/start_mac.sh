#!/usr/bin/env bash
# start_mac.sh — M4 Mac 啟動所有服務
# 用法：bash scripts/start_mac.sh [--no-discord]
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
step()  { echo -e "${CYAN}[STEP]${NC}  $*"; }

NO_DISCORD=false
DISCORD_PID=""
for arg in "$@"; do
    case $arg in
        --no-discord) NO_DISCORD=true ;;
    esac
done

# ── 虛擬環境 ─────────────────────────────────────────────────────────────────
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    warn "找不到 .venv，使用系統 Python（建議先執行 deploy_mac.sh）"
fi

# ── 設定檔檢查 ────────────────────────────────────────────────────────────────
if [ ! -f "config/settings.yaml" ]; then
    echo -e "${YELLOW}[WARN]${NC}  config/settings.yaml 不存在，請先執行 deploy_mac.sh"
    exit 1
fi

# ── 建立日誌目錄 ──────────────────────────────────────────────────────────────
mkdir -p logs

# ── 啟動 Ollama（若未運行）────────────────────────────────────────────────────
if command -v ollama &>/dev/null; then
    if ! pgrep -x ollama &>/dev/null; then
        step "啟動 Ollama..."
        ollama serve > logs/ollama.log 2>&1 &
        sleep 2
        info "Ollama 已啟動，日誌：logs/ollama.log"
    else
        info "Ollama 已在運行"
    fi
else
    warn "找不到 ollama 指令，請先安裝：https://ollama.com"
fi

# ── 啟動 FastAPI 主服務 ───────────────────────────────────────────────────────
step "啟動 Kunomi-core API 服務..."
python main.py > logs/api.log 2>&1 &
API_PID=$!
info "API PID: ${API_PID}  log: logs/api.log"

# 等待 API 起來再啟動其他服務
sleep 2
if ! kill -0 $API_PID 2>/dev/null; then
    echo -e "${RED}[ERROR]${NC} API 服務啟動失敗，請查看 logs/api.log"
    exit 1
fi

# ── 啟動 Discord Bot ──────────────────────────────────────────────────────────
if [ "$NO_DISCORD" = false ]; then
    step "啟動 Discord Bot..."
    python -m discord_bot.bot > logs/discord.log 2>&1 &
    DISCORD_PID=$!
    info "Discord Bot PID: ${DISCORD_PID}  log: logs/discord.log"
else
    warn "跳過 Discord Bot（--no-discord）"
fi

# ── 寫入 PID 檔（方便 stop_mac.sh 停止）─────────────────────────────────────
echo "$API_PID" > logs/api.pid
if [ "$NO_DISCORD" = false ] && [ -n "$DISCORD_PID" ]; then
    echo "$DISCORD_PID" > logs/discord.pid
fi

# ── 完成 ─────────────────────────────────────────────────────────────────────
echo ""
info "═══════════════════════════════════════════════════"
info "  Kunomi-core 已啟動！"
info "  API：    http://localhost:8000/docs"
info "  健康：   curl http://localhost:8000/health"
info "  停止：   bash scripts/stop_mac.sh"
info "  ASR：    在 Windows PC 上按住 ALT 鍵錄音"
info "═══════════════════════════════════════════════════"

# 保持前景運行（Ctrl+C 停止所有服務）
wait $API_PID
