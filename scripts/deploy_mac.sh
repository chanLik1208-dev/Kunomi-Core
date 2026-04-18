#!/usr/bin/env bash
# deploy_mac.sh — M4 Mac 初始部署腳本
# 用法：bash scripts/deploy_mac.sh
set -eu
set -o pipefail 2>/dev/null || true

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 1. Python 版本檢查 ────────────────────────────────────────────────────────
info "檢查 Python 版本..."
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    error "找不到 Python，請先安裝 Python 3.11+"
fi
PY_VER=$("$PYTHON" --version 2>&1) || PY_VER="unknown"
PY_PATH=$(command -v "$PYTHON") || PY_PATH="$PYTHON"
info "Python: ${PY_VER} (${PY_PATH})"

# ── 2. 建立虛擬環境 ───────────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    info "建立虛擬環境 .venv..."
    "$PYTHON" -m venv .venv
else
    info "虛擬環境已存在，跳過建立"
fi

source .venv/bin/activate
info "虛擬環境已啟用"

# ── 3. 安裝依賴 ───────────────────────────────────────────────────────────────
info "安裝 Python 依賴..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
info "依賴安裝完成"

# ── 4. 設定檔初始化 ───────────────────────────────────────────────────────────
if [ ! -f "config/settings.yaml" ]; then
    info "複製設定範本..."
    cp config/settings.example.yaml config/settings.yaml
    warn "請編輯 config/settings.yaml，填入以下必要設定："
    warn "  llm.host         → 127.0.0.1:11434（Ollama 本機）"
    warn "  discord.token    → Discord Bot Token"
    warn "  api.api_key      → 自訂 API 金鑰（任意字串）"
    warn "  pc_agent.host    → 4070 PC 的局域網 IP（port 8100）"
else
    info "config/settings.yaml 已存在，跳過複製"
fi

# ── 5. 建立必要目錄 ───────────────────────────────────────────────────────────
info "建立必要目錄..."
mkdir -p chroma_db screenshots logs

# ── 6. macOS 輔助使用權限提示 ─────────────────────────────────────────────────
if [[ "$OSTYPE" == "darwin"* ]]; then
    warn "macOS 提示：ASR 按鍵發話需要輔助使用權限"
    warn "請前往：系統設定 → 隱私權與安全性 → 輔助使用"
    warn "將 Terminal（或 Python）加入允許清單"
fi

# ── 7. 完成 ───────────────────────────────────────────────────────────────────
echo ""
info "═══════════════════════════════════════════════════"
info "  M4 Mac 部署完成！"
info "  下一步："
info "  1. 安裝 Ollama：https://ollama.com"
info "  2. 拉取模型：ollama pull llama3:8b && ollama pull llava:7b"
info "  3. 編輯 config/settings.yaml（填入 Token / api_key）"
info "  4. 確認 4070 PC 已啟動 PC Agent（port 8100）"
info "  5. 執行：bash scripts/start_mac.sh"
info "═══════════════════════════════════════════════════"
