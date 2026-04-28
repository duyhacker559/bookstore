param(
    [string]$MySqlHost = "127.0.0.1",
    [int]$MySqlPort = 3306,
    [string]$MySqlDatabase = "store",
    [string]$MySqlUser = "store",
    [string]$MySqlPassword = "store_password",
    [string]$DumpFile = "sqlite_export.json"
)

$ErrorActionPreference = "Stop"

function Assert-LastExitCode {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Step (exit code $LASTEXITCODE)"
    }
}

# Prevent Windows codepage/charmap issues when serializing Vietnamese text.
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Write-Host "[1/6] Checking sqlite source..."
if (-not (Test-Path "db.sqlite3")) {
    throw "db.sqlite3 not found in current directory."
}

Write-Host "[2/6] Installing project dependencies..."
python -m pip install -r requirements.txt
Assert-LastExitCode -Step "pip install"

Write-Host "[3/6] Exporting SQLite data to $DumpFile ..."
$env:DJANGO_DB_ENGINE = "sqlite3"
python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --output $DumpFile
Assert-LastExitCode -Step "dumpdata"

Write-Host "[4/6] Switching Django to MySQL env for this shell..."
$env:DJANGO_DB_ENGINE = "mysql"
$env:MYSQL_HOST = $MySqlHost
$env:MYSQL_PORT = "$MySqlPort"
$env:MYSQL_DATABASE = $MySqlDatabase
$env:MYSQL_USER = $MySqlUser
$env:MYSQL_PASSWORD = $MySqlPassword

Write-Host "[5/6] Applying migrations on MySQL..."
python manage.py migrate
Assert-LastExitCode -Step "migrate"

Write-Host "[6/6] Loading exported data into MySQL..."
python manage.py loaddata $DumpFile
Assert-LastExitCode -Step "loaddata"

Write-Host "Done. Verifying with Django check..."
python manage.py check
Assert-LastExitCode -Step "check"

Write-Host "Migration completed successfully."
