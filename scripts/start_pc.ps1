# start_pc.ps1 - Start all services on RTX 4070 PC
# PowerShell -ExecutionPolicy Bypass -File scripts\start_pc.ps1 [-NoOllama] [-NoMinecraft]

param(
    [switch]$NoOllama,
    [switch]$NoMinecraft
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

function Info { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Step { param($msg) Write-Host "[STEP]  $msg" -ForegroundColor Cyan }

# ── venv ──────────────────────────────────────────────────────────────────────
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
} else {
    Warn "No .venv found, using system Python"
}

# ── Config check ──────────────────────────────────────────────────────────────
if (-Not (Test-Path "config\settings.yaml")) {
    Write-Host "[ERROR] config\settings.yaml not found. Run deploy_pc.ps1 first." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# ── Ollama ────────────────────────────────────────────────────────────────────
if (-Not $NoOllama) {
    Step "Starting Ollama..."
    $ollamaProc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if ($ollamaProc) {
        Info "Ollama already running (PID: $($ollamaProc.Id))"
    } else {
        Start-Process -FilePath "ollama" -ArgumentList "serve" `
            -RedirectStandardOutput "logs\ollama.log" `
            -RedirectStandardError "logs\ollama_err.log" `
            -WindowStyle Hidden
        Start-Sleep -Seconds 2
        Info "Ollama started. Log: logs\ollama.log"
    }
} else {
    Warn "Skipping Ollama (-NoOllama)"
}

# ── PC Agent ──────────────────────────────────────────────────────────────────
Step "Starting Kunomi PC Agent (port 8100)..."
$pcAgent = Start-Process -FilePath "python" `
    -ArgumentList "pc_agent\main.py" `
    -RedirectStandardOutput "logs\pc_agent.log" `
    -RedirectStandardError "logs\pc_agent_err.log" `
    -WindowStyle Hidden `
    -PassThru
$pcAgent.Id | Out-File "logs\pc_agent.pid" -Encoding ASCII
Info "PC Agent started (PID: $($pcAgent.Id)). Log: logs\pc_agent.log"

Start-Sleep -Seconds 2
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:8100/health" -Method GET -TimeoutSec 5
    Info "PC Agent health check: OK"
} catch {
    Warn "PC Agent health check failed. Check logs\pc_agent.log"
}

# ── Minecraft log watcher ─────────────────────────────────────────────────────
if (-Not $NoMinecraft) {
    $logPathLine = Select-String -Path "config\settings.yaml" -Pattern "log_path" | Select-Object -First 1
    $hasLogPath = $logPathLine -and $logPathLine.Line -notmatch '""' -and $logPathLine.Line -notmatch "''"

    if ($hasLogPath) {
        Step "Starting Minecraft log watcher..."
        $mcWatcher = Start-Process -FilePath "python" `
            -ArgumentList "-c","from perception.minecraft import start; import time; start(); time.sleep(86400)" `
            -RedirectStandardOutput "logs\mc_watcher.log" `
            -RedirectStandardError "logs\mc_watcher_err.log" `
            -WindowStyle Hidden `
            -PassThru
        $mcWatcher.Id | Out-File "logs\mc_watcher.pid" -Encoding ASCII
        Info "Minecraft watcher started (PID: $($mcWatcher.Id))"
    } else {
        Warn "minecraft.log_path not set, skipping log watcher"
    }
} else {
    Warn "Skipping Minecraft watcher (-NoMinecraft)"
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Info "==================================================="
Info "  4070 PC services started!"
Info "  PC Agent:  http://localhost:8100"
Info "  Ollama:    http://localhost:11434"
Info "  Stop:      .\scripts\stop_pc.ps1"
Info "==================================================="
