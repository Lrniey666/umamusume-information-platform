# Migrate local Django dev (SQLite + media) to Docker PostgreSQL
# Usage: .\scripts\migrate_dev_to_docker.ps1
# Options: -SkipMedia

param(
    [switch]$SkipMedia
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$DumpFile = Join-Path $ProjectRoot "data\dev_sqlite_dump.json"
$SqliteDb = Join-Path $ProjectRoot "db.sqlite3"
$MediaDir = Join-Path $ProjectRoot "media"
$VolumeName = "umamusume-information-platform_media_volume_poa"

Write-Host "=== migrate dev SQLite to Docker PostgreSQL ===" -ForegroundColor Cyan

if (-not (Test-Path $SqliteDb)) {
    throw "Missing db.sqlite3"
}

Write-Host "[1/6] dumpdata from SQLite..."
$env:DJANGO_DB_ENGINE = "sqlite"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
Remove-Item Env:POSTGRES_HOST -ErrorAction SilentlyContinue
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 --output $DumpFile
if ($LASTEXITCODE -ne 0) { throw "dumpdata failed" }
$dumpSizeMb = [math]::Round((Get-Item $DumpFile).Length / 1MB, 2)
Write-Host "  done: $DumpFile ($dumpSizeMb MB)" -ForegroundColor Green

Write-Host "[2/6] stop web / discord-bot / nginx..."
docker compose stop web-poa discord-bot nginx | Out-Null

Write-Host "[3/6] flush and loaddata..."
docker compose up -d db | Out-Null
Start-Sleep -Seconds 3
docker compose run --rm --no-deps web-poa python manage.py flush --no-input
if ($LASTEXITCODE -ne 0) { throw "flush failed" }
docker compose run --rm --no-deps web-poa python manage.py loaddata /app/data/dev_sqlite_dump.json
if ($LASTEXITCODE -ne 0) { throw "loaddata failed" }

Write-Host "[4/6] reset PostgreSQL sequences..."
docker compose run --rm --no-deps web-poa python scripts/reset_postgres_sequences.py
if ($LASTEXITCODE -ne 0) { throw "reset sequences failed" }

if (-not $SkipMedia) {
    Write-Host "[5/6] sync media to Docker volume..."
    if (Test-Path $MediaDir) {
        docker run --rm -v "${VolumeName}:/dest" -v "${MediaDir}:/src:ro" alpine sh -c "mkdir -p /dest; cp -a /src/. /dest/"
        if ($LASTEXITCODE -ne 0) { throw "media sync failed" }
    } else {
        Write-Host "  skip: local media/ not found" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "[5/6] skip media sync (-SkipMedia)" -ForegroundColor DarkYellow
}

Write-Host "[6/6] restart all services..."
docker compose up -d
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

Write-Host "=== migration complete ===" -ForegroundColor Green
Write-Host "http://localhost/"
Write-Host "http://localhost/crawler-admin/"
Write-Host "http://localhost/uma-info/"
