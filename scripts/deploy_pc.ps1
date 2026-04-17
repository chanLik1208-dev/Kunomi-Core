# deploy_pc.ps1 — RTX 4070 PC 初始部署腳本（PowerShell）
# 用法：PowerShell -ExecutionPolicy Bypass -File scripts\deploy_pc.ps1

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

function Info  { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Green }
function Warn  { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Err   { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

# ── 1. Python 版本檢查 ────────────────────────────────────────────────────────
Info "檢查 Python 版本..."
try {
    $pyVer = python --version 2>&1
    Info "Python：$pyVer"
} catch {
    Err "找不到 Python，請先安裝 Python 3.11+"
}

# ── 2. 建立虛擬環境 ───────────────────────────────────────────────────────────
if (-Not (Test-Path ".venv")) {
    Info "建立虛擬環境 .venv..."
    python -m venv .venv
} else {
    Info "虛擬環境已存在，跳過建立"
}

& .\.venv\Scripts\Activate.ps1
Info "虛擬環境已啟用"

# ── 3. 安裝 M4 Mac 依賴（共用 core / config / tools）────────────────────────
Info "安裝共用依賴..."
pip install --upgrade pip -q
pip install fastapi uvicorn httpx pyyaml -q

# ── 4. 安裝 PC 專屬依賴 ───────────────────────────────────────────────────────
Info "安裝 PC 專屬依賴（dxcam / opencv / pygame）..."
pip install opencv-python pygame -q

# dxcam 需要特殊安裝方式
try {
    python -c "import dxcam" 2>$null
    Info "dxcam 已安裝"
} catch {
    Warn "安裝 dxcam..."
    pip install dxcam -q
}

# ── 5. 設定檔初始化 ───────────────────────────────────────────────────────────
if (-Not (Test-Path "config\settings.yaml")) {
    Info "複製設定範本..."
    Copy-Item "config\settings.example.yaml" "config\settings.yaml"
    Warn "請編輯 config\settings.yaml，填入以下必要設定："
    Warn "  llm.host          → 本機（127.0.0.1）或實際 IP"
    Warn "  api.api_key       → 與 M4 Mac 相同的 API 金鑰"
    Warn "  pc_agent.api_key  → 自訂 PC Agent 金鑰"
    Warn "  minecraft.log_path → MC 伺服器日誌路徑（如有）"
} else {
    Info "config\settings.yaml 已存在，跳過複製"
}

# ── 6. 建立必要目錄 ───────────────────────────────────────────────────────────
Info "建立必要目錄..."
New-Item -ItemType Directory -Force -Path "screenshots", "logs", "assets\sounds" | Out-Null

# ── 7. 檢查 Ollama ────────────────────────────────────────────────────────────
Info "檢查 Ollama 安裝狀態..."
try {
    $ollamaVer = ollama --version 2>&1
    Info "Ollama：$ollamaVer"
} catch {
    Warn "Ollama 未安裝或不在 PATH 中"
    Warn "請前往 https://ollama.com 下載並安裝"
    Warn "安裝後執行：ollama pull llama3:8b && ollama pull llava:7b"
}

# ── 8. 防火牆規則（port 8100）────────────────────────────────────────────────
Info "設定防火牆規則（允許區網存取 port 8100）..."
$ruleName = "Kunomi-PC-Agent"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-Not $existing) {
    New-NetFirewallRule `
        -DisplayName $ruleName `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort 8100 `
        -Action Allow `
        -Profile Private | Out-Null
    Info "防火牆規則已建立（port 8100 / 私人網路）"
} else {
    Info "防火牆規則已存在，跳過"
}

# ── 9. 完成 ───────────────────────────────────────────────────────────────────
Write-Host ""
Info "═══════════════════════════════════════════════════"
Info "  4070 PC 部署完成！"
Info "  下一步："
Info "  1. 編輯 config\settings.yaml"
Info "  2. 執行：ollama pull llama3:8b"
Info "  3. 執行：ollama pull llava:7b"
Info "  4. 放入音效檔到 assets\sounds\"
Info "  5. 執行：.\scripts\start_pc.ps1"
Info "═══════════════════════════════════════════════════"
