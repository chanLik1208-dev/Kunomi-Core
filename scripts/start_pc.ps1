# start_pc.ps1 - Start Kunomi PC Agent (TTS playback + STT)
# PowerShell -ExecutionPolicy Bypass -File scripts\start_pc.ps1

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

# ── PC Agent ──────────────────────────────────────────────────────────────────
Step "Starting Kunomi PC Agent (port 8100)..."
$pcAgent = Start-Process -FilePath "python" `
    -ArgumentList "pc_agent\main.py" `
    -WorkingDirectory $ProjectDir `
    -RedirectStandardOutput "$ProjectDir\logs\pc_agent.log" `
    -RedirectStandardError "$ProjectDir\logs\pc_agent_err.log" `
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

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Info "==================================================="
Info "  PC services started!"
Info "  PC Agent:  http://localhost:8100"
Info "  STT:       Hold ALT to record (started by PC Agent)"
Info "  TTS:       Audio played here (OBS can capture)"
Info "  Stop:      .\scripts\stop_pc.ps1"
Info "==================================================="
