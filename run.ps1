param (
    [string]$Mode = "dev"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$BackendVenv = Join-Path $ScriptDir "backend\.venv\Scripts\python.exe"

if ($Mode -eq "space") {
    Write-Host "==> Launching Unified AI Legal Intelligence Platform (Port 7860)..." -ForegroundColor Green
    & $BackendVenv space_app.py
    exit $LASTEXITCODE
}

Write-Host "==> Starting AI Legal Document Intelligence Platform..." -ForegroundColor Cyan

Write-Host "==> Starting FastAPI Backend (http://localhost:8000)..." -ForegroundColor Green
$BackendProc = Start-Process -FilePath $BackendVenv -ArgumentList "-m uvicorn app.main:app --reload --port 8000" -WorkingDirectory (Join-Path $ScriptDir "backend") -PassThru

Write-Host "==> Starting React Frontend (http://localhost:5173)..." -ForegroundColor Green
Set-Location (Join-Path $ScriptDir "frontend")

try {
    npm run dev
} finally {
    if ($BackendProc -and -not $BackendProc.HasExited) {
        Write-Host "Stopping FastAPI backend..." -ForegroundColor Yellow
        Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue
    }
}
