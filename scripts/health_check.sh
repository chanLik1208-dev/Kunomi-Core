#!/usr/bin/env bash
# health_check.sh — 檢查所有服務健康狀態
# 用法：bash scripts/health_check.sh

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC}  $*"; }
fail() { echo -e "  ${RED}✗${NC}  $*"; }
warn() { echo -e "  ${YELLOW}?${NC}  $*"; }

# 讀取設定
if [ -f "config/settings.yaml" ]; then
    MAC_PORT=$(python3 -c "import yaml; c=yaml.safe_load(open('config/settings.yaml')); print(c['api']['port'])" 2>/dev/null || echo "8000")
    PC_HOST=$(python3 -c "import yaml; c=yaml.safe_load(open('config/settings.yaml')); print(c.get('pc_agent',{}).get('host','http://localhost:8100'))" 2>/dev/null || echo "http://localhost:8100")
    LLM_HOST=$(python3 -c "import yaml; c=yaml.safe_load(open('config/settings.yaml')); print(c['llm']['host'])" 2>/dev/null || echo "http://localhost:11434")
else
    MAC_PORT="8000"
    PC_HOST="http://localhost:8100"
    LLM_HOST="http://localhost:11434"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Kunomi-core 健康檢查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# M4 Mac API
echo ""
echo "[ M4 Mac ]"
if curl -sf "http://localhost:${MAC_PORT}/health" -o /dev/null 2>/dev/null; then
    ok "FastAPI (port ${MAC_PORT})"
else
    fail "FastAPI (port ${MAC_PORT}) — 未啟動"
fi

# 4070 PC Agent
echo ""
echo "[ 4070 PC Agent ]"
if curl -sf "${PC_HOST}/health" -o /dev/null 2>/dev/null; then
    ok "PC Agent (${PC_HOST})"
else
    fail "PC Agent (${PC_HOST}) — 未啟動或無法連線"
fi

# Ollama LLM
echo ""
echo "[ Ollama LLM ]"
if curl -sf "${LLM_HOST}/api/tags" -o /dev/null 2>/dev/null; then
    ok "Ollama (${LLM_HOST})"
    # 列出已安裝的模型
    MODELS=$(curl -sf "${LLM_HOST}/api/tags" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
names = [m['name'] for m in data.get('models', [])]
print(', '.join(names) if names else '（無模型）')
" 2>/dev/null || echo "（無法解析）")
    echo "     模型：$MODELS"
else
    fail "Ollama (${LLM_HOST}) — 未啟動或無法連線"
fi

# ChromaDB
echo ""
echo "[ ChromaDB ]"
if [ -d "chroma_db" ]; then
    ok "chroma_db 資料夾存在"
else
    warn "chroma_db 尚未建立（首次呼叫記憶功能時自動建立）"
fi

# Discord Bot PID
echo ""
echo "[ Discord Bot ]"
if [ -f "logs/discord.pid" ]; then
    DPID=$(cat logs/discord.pid)
    if kill -0 "$DPID" 2>/dev/null; then
        ok "Discord Bot 運行中（PID: $DPID）"
    else
        fail "Discord Bot PID 檔存在但行程已死（PID: $DPID）"
    fi
else
    warn "Discord Bot PID 檔不存在"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
