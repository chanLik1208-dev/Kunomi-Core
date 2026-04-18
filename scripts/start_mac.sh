#!/usr/bin/env bash
# start_mac.sh — M4 Mac start all services
# Usage: bash scripts/start_mac.sh [--no-discord]
set -eu
set -o pipefail 2>/dev/null || true

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

# ── venv ──────────────────────────────────────────────────────────────────────
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    warn "No .venv found. Run deploy_mac.sh first."
fi

# ── Config check ──────────────────────────────────────────────────────────────
if [ ! -f "config/settings.yaml" ]; then
    warn "config/settings.yaml not found. Run deploy_mac.sh first."
    exit 1
fi

mkdir -p logs

# ── Ollama ────────────────────────────────────────────────────────────────────
if command -v ollama &>/dev/null; then
    if ! pgrep -x ollama &>/dev/null; then
        step "Starting Ollama..."
        ollama serve > logs/ollama.log 2>&1 &
        sleep 2
        info "Ollama started. log: logs/ollama.log"
    else
        info "Ollama already running."
    fi
else
    warn "ollama not found. Install from https://ollama.com"
fi

# ── FastAPI ───────────────────────────────────────────────────────────────────
step "Starting Kunomi-core API..."
python3 main.py > logs/api.log 2>&1 &
API_PID=$!
info "API PID: ${API_PID}  log: logs/api.log"

sleep 2
if ! kill -0 ${API_PID} 2>/dev/null; then
    echo -e "${RED}[ERROR]${NC} API failed to start. Check logs/api.log"
    cat logs/api.log
    exit 1
fi

# ── Discord Bot ───────────────────────────────────────────────────────────────
if [ "$NO_DISCORD" = false ]; then
    step "Starting Discord Bot..."
    python3 -m discord_bot.bot > logs/discord.log 2>&1 &
    DISCORD_PID=$!
    info "Discord Bot PID: ${DISCORD_PID}  log: logs/discord.log"
else
    warn "Skipping Discord Bot (--no-discord)"
fi

# ── PID files ─────────────────────────────────────────────────────────────────
echo "${API_PID}" > logs/api.pid
if [ "$NO_DISCORD" = false ] && [ -n "$DISCORD_PID" ]; then
    echo "${DISCORD_PID}" > logs/discord.pid
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
info "==================================================="
info "  Kunomi-core started!"
info "  API:      http://localhost:8000/docs"
info "  Health:   curl http://localhost:8000/health"
info "  Dashboard: http://localhost:8000/dashboard"
info "  Stop:     bash scripts/stop_mac.sh"
info "  STT:      Hold ALT on Windows PC to record"
info "==================================================="

wait ${API_PID}
