# deploy_pc.ps1 - RTX 4070 PC
# PowerShell -ExecutionPolicy Bypass -File scripts\deploy_pc.ps1

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

function Info { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Fail { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

# ── 1. Python ─────────────────────────────────────────────────────────────────
Info "Python version check..."
$pyCheck = & python --version 2>&1
if ($LASTEXITCODE -ne 0) { Fail "Python not found. Please install Python 3.11+" }
Info "Python: $pyCheck"

# ── 2. venv ───────────────────────────────────────────────────────────────────
if (-Not (Test-Path ".venv")) {
    Info "Creating virtual environment .venv..."
    python -m venv .venv
} else {
    Info ".venv already exists, skipping"
}

& .\.venv\Scripts\Activate.ps1
Info "Virtual environment activated"

# ── 3. Common dependencies ────────────────────────────────────────────────────
Info "Installing shared dependencies..."
pip install --upgrade pip -q
pip install fastapi "uvicorn[standard]" httpx pyyaml -q

# ── 4. PC-only dependencies ───────────────────────────────────────────────────
Info "Installing PC-only dependencies (opencv / pygame)..."
pip install opencv-python pygame -q

# dxcam check
$dxcamResult = & python -c "import dxcam; print('ok')" 2>&1
if ($dxcamResult -eq "ok") {
    Info "dxcam already installed"
} else {
    Info "Installing dxcam..."
    pip install dxcam -q
}

# ── 5. Config ─────────────────────────────────────────────────────────────────
if (-Not (Test-Path "config\settings.yaml")) {
    Info "Copying settings template..."
    Copy-Item "config\settings.example.yaml" "config\settings.yaml"
    Warn "Please edit config\settings.yaml:"
    Warn "  llm.host         -> 127.0.0.1 (local Ollama)"
    Warn "  api.api_key      -> same key as M4 Mac"
    Warn "  pc_agent.api_key -> any secret string"
    Warn "  minecraft.log_path -> path to latest.log (optional)"
} else {
    Info "config\settings.yaml already exists, skipping"
}

# ── 6. Directories ────────────────────────────────────────────────────────────
Info "Creating required directories..."
New-Item -ItemType Directory -Force -Path "screenshots","logs","assets\sounds" | Out-Null

# ── 7. Ollama check ───────────────────────────────────────────────────────────
Info "Checking Ollama..."
$ollamaCheck = & ollama --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Info "Ollama: $ollamaCheck"
} else {
    Warn "Ollama not found or not in PATH"
    Warn "Download from: https://ollama.com"
    Warn "After install, run: ollama pull llama3:8b"
    Warn "Then run:           ollama pull llava:7b"
}

# ── 8. Firewall rule (port 8100) ──────────────────────────────────────────────
Info "Setting firewall rule (port 8100)..."
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
    Info "Firewall rule created (port 8100, Private network)"
} else {
    Info "Firewall rule already exists, skipping"
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Info "==================================================="
Info "  4070 PC deployment complete!"
Info "  Next steps:"
Info "  1. Edit config\settings.yaml"
Info "  2. Run: ollama pull llama3:8b"
Info "  3. Run: ollama pull llava:7b"
Info "  4. Put sound files in assets\sounds\"
Info "  5. Run: .\scripts\start_pc.ps1"
Info "==================================================="
