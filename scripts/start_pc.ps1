# start_pc.ps1 — RTX 4070 PC 啟動所有服務
# 用法：PowerShell -ExecutionPolicy Bypass -File scripts\start_pc.ps1 [--no-ollama] [--no-mc]

param(
    [switch]$NoOllama,
    [switch]$NoMinecraft
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

function Info  { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Green }
function Warn  { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Step  { param($msg) Write-Host "[STEP]  $msg" -ForegroundColor Cyan }

# ── 虛擬環境 ─────────────────────────────────────────────────────────────────
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
} else {
    Warn "找不到 .venv，使用系統 Python（建議先執行 deploy_pc.ps1）"
}

# ── 設定檔檢查 ────────────────────────────────────────────────────────────────
if (-Not (Test-Path "config\settings.yaml")) {
    Write-Host "[ERROR] config\settings.yaml 不存在，請先執行 deploy_pc.ps1" -ForegroundColor Red
    exit 1
}

# 建立日誌目錄
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# ── 啟動 Ollama ───────────────────────────────────────────────────────────────
if (-Not $NoOllama) {
    Step "啟動 Ollama 服務..."
    $ollamaProc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if ($ollamaProc) {
        Info "Ollama 已在運行（PID: $($ollamaProc.Id)）"
    } else {
        Start-Process -FilePath "ollama" -ArgumentList "serve" `
            -RedirectStandardOutput "logs\ollama.log" `
            -RedirectStandardError "logs\ollama_err.log" `
            -WindowStyle Hidden
        Start-Sleep -Seconds 2
        Info "Ollama 已啟動，日誌：logs\ollama.log"
    }
} else {
    Warn "跳過 Ollama（-NoOllama）"
}

# ── 啟動 PC Agent ─────────────────────────────────────────────────────────────
Step "啟動 Kunomi PC Agent（port 8100）..."
$pcAgent = Start-Process -FilePath "python" `
    -ArgumentList "pc_agent\main.py" `
    -RedirectStandardOutput "logs\pc_agent.log" `
    -RedirectStandardError "logs\pc_agent_err.log" `
    -WindowStyle Hidden `
    -PassThru
$pcAgent.Id | Out-File "logs\pc_agent.pid"
Info "PC Agent 已啟動（PID: $($pcAgent.Id)），日誌：logs\pc_agent.log"

# 等待 PC Agent 啟動
Start-Sleep -Seconds 2
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:8100/health" -Method GET -TimeoutSec 5
    Info "PC Agent 健康確認：OK"
} catch {
    Warn "PC Agent 健康檢查失敗，請查看 logs\pc_agent.log"
}

# ── 啟動 Minecraft 日誌監聽 ───────────────────────────────────────────────────
if (-Not $NoMinecraft) {
    # 讀取設定確認 log_path 是否已設定
    $settings = Get-Content "config\settings.yaml" | Where-Object { $_ -match "log_path" }
    if ($settings -match '""' -or $settings -match "''") {
        Warn "minecraft.log_path 未設定，跳過日誌監聽"
    } else {
        Step "啟動 Minecraft 日誌監聽..."
        $mcWatcher = Start-Process -FilePath "python" `
            -ArgumentList "-c", "from perception.minecraft import start; import time; start(); time.sleep(9999999)" `
            -RedirectStandardOutput "logs\mc_watcher.log" `
            -RedirectStandardError "logs\mc_watcher_err.log" `
            -WindowStyle Hidden `
            -PassThru
        $mcWatcher.Id | Out-File "logs\mc_watcher.pid"
        Info "Minecraft 監聽已啟動（PID: $($mcWatcher.Id)）"
    }
} else {
    Warn "跳過 Minecraft 監聽（-NoMinecraft）"
}

# ── 完成 ─────────────────────────────────────────────────────────────────────
Write-Host ""
Info "═══════════════════════════════════════════════════"
Info "  4070 PC 服務已啟動！"
Info "  PC Agent： http://localhost:8100"
Info "  Ollama：   http://localhost:11434"
Info "  停止：     .\scripts\stop_pc.ps1"
Info "═══════════════════════════════════════════════════"
