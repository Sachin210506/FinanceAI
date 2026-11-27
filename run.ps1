Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " FinanceAI - 2-Agent Hybrid RAG (Ollama 2.5 1.5B) " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$ollamaExe = Join-Path (Split-Path $PSScriptRoot -Parent) "ollama\ollama.exe"
if (Test-Path $ollamaExe) {
    Write-Host "[1/2] Checking local Ollama server..." -ForegroundColor Yellow
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
    } catch {
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
    }
}

Write-Host "[2/2] Starting FinanceAI at http://127.0.0.1:8002 ..." -ForegroundColor Green
$backend = Join-Path $PSScriptRoot "backend"
$venv = Join-Path $backend ".venv" 
$python = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $python)) {
    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $systemPython) {
        throw "Python 3.12 or later is required to create backend\.venv."
    }

    Write-Host "Creating FinanceAI's local Python environment..." -ForegroundColor Yellow
    & $systemPython.Source -m venv --system-site-packages $venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create FinanceAI's Python environment." }
}

$setupMarker = Join-Path $venv ".requirements-installed"
if (-not (Test-Path $setupMarker)) {
    & $python -m pip install -r (Join-Path $backend "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Could not install FinanceAI's Python requirements." }
    Set-Content -Path $setupMarker -Value "Installed"
}

Set-Location $backend
& $python -m uvicorn server:app --host 127.0.0.1 --port 8002
