# stop_pc.ps1 - Stop all Kunomi services on 4070 PC

$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

function Info { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }

function Stop-ByPidFile {
    param($name, $pidfile)
    $path = "logs\$pidfile.pid"
    if (Test-Path $path) {
        $id = [int](Get-Content $path)
        $proc = Get-Process -Id $id -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $id -Force
            Info "$name stopped (PID: $id)"
        } else {
            Warn "$name is not running (PID: $id)"
        }
        Remove-Item $path -Force
    } else {
        Warn "$name PID file not found ($path)"
    }
}

Stop-ByPidFile "PC Agent"          "pc_agent"
Stop-ByPidFile "Minecraft watcher" "mc_watcher"

Info "All PC services stopped."
