# stop_pc.ps1 — 停止 4070 PC 上所有 Kunomi 服務

$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

function Info  { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Green }
function Warn  { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }

function Stop-ByPidFile {
    param($name, $pidfile)
    $path = "logs\$pidfile.pid"
    if (Test-Path $path) {
        $pid = Get-Content $path
        try {
            Stop-Process -Id $pid -Force
            Info "$name 已停止（PID: $pid）"
        } catch {
            Warn "$name 已不在運行（PID: $pid）"
        }
        Remove-Item $path -Force
    } else {
        Warn "找不到 $name PID 檔（$path）"
    }
}

Stop-ByPidFile "PC Agent"          "pc_agent"
Stop-ByPidFile "Minecraft 監聽"     "mc_watcher"

Info "所有 PC 服務已停止"
Info "注意：Ollama 服務需手動停止（工作列右鍵 → 退出）"
