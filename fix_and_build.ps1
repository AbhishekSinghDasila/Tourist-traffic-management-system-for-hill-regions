# ============================================================
# DevBhumi — Windows DNS Fix + Build Script
# Run this in PowerShell AS ADMINISTRATOR
# Right-click PowerShell → "Run as Administrator"
# Then: cd E:\DevBhumi && .\fix_and_build.ps1
# ============================================================

Write-Host ""
Write-Host "=== DevBhumi: Fixing Docker DNS and rebuilding ===" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Apply Docker daemon DNS config ──────────────────
$daemonPath = "$env:APPDATA\Docker\daemon.json"
$daemonConfig = @{
    dns        = @("8.8.8.8", "8.8.4.4", "1.1.1.1")
    "dns-opts" = @("ndots:1")
    "dns-search" = @()
} | ConvertTo-Json

Write-Host "Step 1: Writing Docker daemon DNS config to $daemonPath" -ForegroundColor Yellow

# Backup existing daemon.json if it exists
if (Test-Path $daemonPath) {
    Copy-Item $daemonPath "$daemonPath.backup"
    Write-Host "  Backed up existing daemon.json to daemon.json.backup" -ForegroundColor Gray

    # Merge with existing config instead of overwriting
    $existing = Get-Content $daemonPath | ConvertFrom-Json
    $existing | Add-Member -NotePropertyName "dns" -NotePropertyValue @("8.8.8.8","8.8.4.4","1.1.1.1") -Force
    $existing | Add-Member -NotePropertyName "dns-opts" -NotePropertyValue @("ndots:1") -Force
    $existing | Add-Member -NotePropertyName "dns-search" -NotePropertyValue @() -Force
    $existing | ConvertTo-Json | Set-Content $daemonPath
} else {
    $daemonConfig | Set-Content $daemonPath
}

Write-Host "  Done." -ForegroundColor Green

# ── Step 2: Restart Docker Desktop ─────────────────────────
Write-Host ""
Write-Host "Step 2: Restarting Docker Desktop to apply DNS settings..." -ForegroundColor Yellow
Write-Host "  This will take 20-40 seconds. Please wait." -ForegroundColor Gray

# Kill Docker Desktop
$dockerProcesses = @("Docker Desktop", "com.docker.backend", "com.docker.proxy")
foreach ($proc in $dockerProcesses) {
    $p = Get-Process -Name $proc -ErrorAction SilentlyContinue
    if ($p) {
        Stop-Process -Name $proc -Force -ErrorAction SilentlyContinue
        Write-Host "  Stopped: $proc" -ForegroundColor Gray
    }
}

Start-Sleep -Seconds 5

# Start Docker Desktop
$dockerPath = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerPath) {
    Start-Process $dockerPath
    Write-Host "  Starting Docker Desktop..." -ForegroundColor Gray
} else {
    Write-Host "  Docker Desktop not found at $dockerPath" -ForegroundColor Red
    Write-Host "  Please start Docker Desktop manually and press Enter when ready." -ForegroundColor Yellow
    Read-Host
}

# Wait for Docker to be ready
Write-Host "  Waiting for Docker daemon to be ready..." -ForegroundColor Gray
$maxWait = 60
$waited = 0
do {
    Start-Sleep -Seconds 3
    $waited += 3
    $ready = & docker info 2>$null
    Write-Host "  Waiting... ($waited s)" -ForegroundColor Gray
} while ($LASTEXITCODE -ne 0 -and $waited -lt $maxWait)

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Docker did not start in time. Please:" -ForegroundColor Red
    Write-Host "  1. Open Docker Desktop manually" -ForegroundColor White
    Write-Host "  2. Wait for it to show 'Engine running'" -ForegroundColor White
    Write-Host "  3. Run: docker compose up -d --build" -ForegroundColor White
    exit 1
}

Write-Host "  Docker is ready." -ForegroundColor Green

# ── Step 3: Clear any failed build cache ───────────────────
Write-Host ""
Write-Host "Step 3: Clearing failed build cache..." -ForegroundColor Yellow
docker builder prune -f 2>$null
Write-Host "  Done." -ForegroundColor Green

# ── Step 4: Build and start everything ─────────────────────
Write-Host ""
Write-Host "Step 4: Building and starting all containers..." -ForegroundColor Yellow
Write-Host "  This will take 3-7 minutes on first run (downloading Python packages)." -ForegroundColor Gray
Write-Host ""

docker compose up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== Build succeeded! ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting 15 seconds for services to initialize..." -ForegroundColor Gray
    Start-Sleep -Seconds 15

    Write-Host ""
    Write-Host "Container status:" -ForegroundColor Cyan
    docker compose ps

    Write-Host ""
    Write-Host "Testing auth-service health..." -ForegroundColor Cyan
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "  Auth service is UP and healthy!" -ForegroundColor Green
        Write-Host "  API docs: http://localhost:8001/docs" -ForegroundColor Cyan
    } else {
        Write-Host "  Auth service not responding yet. Run: docker compose logs auth-service" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "=== Build failed ===" -ForegroundColor Red
    Write-Host "Run this to see detailed error logs:" -ForegroundColor Yellow
    Write-Host "  docker compose logs auth-service" -ForegroundColor White
}
