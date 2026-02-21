param(
    [Parameter(Mandatory = $true)]
    [string]$suffix,

    [string]$dbonly = "true",

    [string]$background = "false",

    [string]$dbtype = ""
)

# Backup Data Script
# - SQLite mode: archives coins.db and optionally HTML to a .7z file.
# - Postgres mode: runs pg_dump and copies a .dump file to local backup dir.

# Configuration
$sevenZipPath = "C:\Program Files\7-Zip\7z.exe"

function ConvertTo-Bool {
    param(
        [Parameter(Mandatory = $true)]
        [string]$value,
        [Parameter(Mandatory = $true)]
        [string]$name
    )

    switch ($value.Trim().ToLowerInvariant()) {
        "1" { return $true }
        "true" { return $true }
        "`$true" { return $true }
        "yes" { return $true }
        "y" { return $true }
        "0" { return $false }
        "false" { return $false }
        "`$false" { return $false }
        "no" { return $false }
        "n" { return $false }
        default {
            throw "$name must be one of true/false/1/0/yes/no."
        }
    }
}

function ConvertTo-DbType {
    param(
        [string]$value
    )

    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "dbtype is required. Use: s|sqlite|p|postgres|postgresql."
    }

    $normalized = $value.Trim().ToLowerInvariant()
    switch ($normalized) {
        "s" { return "s" }
        "sqlite" { return "s" }
        "p" { return "p" }
        "postgres" { return "p" }
        "postgresql" { return "p" }
        default {
            throw "dbtype must be one of: s|sqlite|p|postgres|postgresql."
        }
    }
}

function Write-BackupMeta {
    param(
        [Parameter(Mandatory = $true)]
        [string]$logsDir,
        [Parameter(Mandatory = $true)]
        [hashtable]$meta
    )

    $metaPath = Join-Path $logsDir "last_backup.json"
    $meta | ConvertTo-Json -Depth 6 | Set-Content -Path $metaPath -Encoding UTF8
    return $metaPath
}

$dbOnlyEnabled = ConvertTo-Bool -value $dbonly -name "dbonly"
$runInBackground = ConvertTo-Bool -value $background -name "background"
$dbType = ConvertTo-DbType -value $dbtype

$normalizedSuffix = $suffix.Trim()
if ([string]::IsNullOrWhiteSpace($normalizedSuffix)) {
    throw "suffix cannot be empty."
}

# Allow passing with or without extension
$normalizedSuffix = $normalizedSuffix -replace "\.(7z|dump)$", ""
$datePart = Get-Date -Format "yyyy_MM_dd"

if ($dbType -eq "s") {
    $backupDir = "D:\bkp\numista_bkp"
    $backupFile = "numista_${datePart}_${normalizedSuffix}.7z"
    $backupPath = Join-Path $backupDir $backupFile
    $logsDir = Join-Path $backupDir "logs"
    $sourceHtml = "D:\projects\mintada\scrappers\numista\coin_types\html"
    $sourceDb = "D:\projects\mintada\data\numista\coins.db"

    if (-not (Test-Path $sevenZipPath)) {
        throw "7-Zip not found at $sevenZipPath."
    }

    if (-not (Test-Path $backupDir)) {
        Write-Host "Creating backup directory: $backupDir"
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    }
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    }

    Write-Host "Creating SQLite backup archive at: $backupPath" -ForegroundColor Cyan
    Write-Host "Sources:"
    Write-Host " - $sourceDb"
    if (-not $dbOnlyEnabled) {
        Write-Host " - $sourceHtml"
    }

    $args = @("a", $backupPath, $sourceDb)
    if (-not $dbOnlyEnabled) {
        $args += $sourceHtml
    }

    if ($runInBackground) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $stdoutLog = Join-Path $logsDir "backup_${timestamp}_${normalizedSuffix}.out.log"
        $stderrLog = Join-Path $logsDir "backup_${timestamp}_${normalizedSuffix}.err.log"

        $process = Start-Process -FilePath $sevenZipPath `
            -ArgumentList $args `
            -PassThru `
            -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError $stderrLog

        Write-Host "Backup started in background." -ForegroundColor Green
        Write-Host "PID: $($process.Id)"
        Write-Host "Archive: $backupPath"
        Write-Host "StdOut log: $stdoutLog"
        Write-Host "StdErr log: $stderrLog"

        $meta = @{
            status = "started"
            startedAt = (Get-Date).ToString("o")
            pid = $process.Id
            archivePath = $backupPath
            stdoutLog = $stdoutLog
            stderrLog = $stderrLog
            suffix = $normalizedSuffix
            dbonly = $dbOnlyEnabled
            background = $runInBackground
            dbtype = "s"
        }
        $metaPath = Write-BackupMeta -logsDir $logsDir -meta $meta

        Write-Output "BACKGROUND_PID=$($process.Id)"
        Write-Output "ARCHIVE_PATH=$backupPath"
        Write-Output "STDOUT_LOG=$stdoutLog"
        Write-Output "STDERR_LOG=$stderrLog"
        Write-Output "META_PATH=$metaPath"
        return
    }

    Write-Host "& '$sevenZipPath' $args"
    & $sevenZipPath @args

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Backup completed successfully." -ForegroundColor Green
        $meta = @{
            status = "completed"
            completedAt = (Get-Date).ToString("o")
            exitCode = $LASTEXITCODE
            archivePath = $backupPath
            suffix = $normalizedSuffix
            dbonly = $dbOnlyEnabled
            background = $runInBackground
            dbtype = "s"
        }
        $metaPath = Write-BackupMeta -logsDir $logsDir -meta $meta
        Write-Output "ARCHIVE_PATH=$backupPath"
        Write-Output "META_PATH=$metaPath"
    } else {
        Write-Host "7-Zip failed with exit code $LASTEXITCODE" -ForegroundColor Red
        $meta = @{
            status = "failed"
            failedAt = (Get-Date).ToString("o")
            exitCode = $LASTEXITCODE
            archivePath = $backupPath
            suffix = $normalizedSuffix
            dbonly = $dbOnlyEnabled
            background = $runInBackground
            dbtype = "s"
        }
        $metaPath = Write-BackupMeta -logsDir $logsDir -meta $meta
        Write-Output "META_PATH=$metaPath"
    }
    return
}

# Postgres branch
$backupDir = "D:\bkp\numista_bkp"
$backupFile = "numista_pg_${datePart}_${normalizedSuffix}.dump"
$backupPath = Join-Path $backupDir $backupFile
$logsDir = Join-Path $backupDir "logs"

if (-not (Test-Path $backupDir)) {
    Write-Host "Creating backup directory: $backupDir"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

if ($dbOnlyEnabled -eq $false) {
    Write-Host "dbonly=false is ignored for Postgres backups (database-only)." -ForegroundColor Yellow
}
if ($runInBackground) {
    Write-Host "background=true is not supported for Postgres dump mode. Running in foreground." -ForegroundColor Yellow
    $runInBackground = $false
}

$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($null -eq $dockerCmd) {
    throw "docker command not found in PATH."
}

$pgContainer = "mintada-db"
$pgDb = "mintada_db"
$pgUser = "admin"
$pgPassword = "mintada"
$containerDumpPath = "/tmp/$backupFile"

Write-Host "Creating Postgres dump at: $backupPath" -ForegroundColor Cyan
Write-Host "Container: $pgContainer"
Write-Host "Database: $pgDb"

# Ensure stale temporary file does not interfere.
& docker exec $pgContainer sh -c "rm -f '$containerDumpPath'" | Out-Null

$dumpArgs = @(
    "exec",
    "-e", "PGPASSWORD=$pgPassword",
    $pgContainer,
    "pg_dump",
    "-U", $pgUser,
    "-d", $pgDb,
    "-Fc",
    "-f", $containerDumpPath
)

& docker @dumpArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "pg_dump failed with exit code $LASTEXITCODE" -ForegroundColor Red
    $meta = @{
        status = "failed"
        failedAt = (Get-Date).ToString("o")
        exitCode = $LASTEXITCODE
        archivePath = $backupPath
        suffix = $normalizedSuffix
        dbonly = $dbOnlyEnabled
        background = $runInBackground
        dbtype = "p"
        container = $pgContainer
        database = $pgDb
    }
    $metaPath = Write-BackupMeta -logsDir $logsDir -meta $meta
    Write-Output "META_PATH=$metaPath"
    throw "Postgres dump command failed."
}

$copyArgs = @("cp", "$pgContainer`:$containerDumpPath", $backupPath)
& docker @copyArgs
$copyExitCode = $LASTEXITCODE

# Best-effort cleanup of temporary dump file in container.
& docker exec $pgContainer sh -c "rm -f '$containerDumpPath'" | Out-Null

if ($copyExitCode -eq 0) {
    Write-Host "Postgres backup completed successfully." -ForegroundColor Green
    $meta = @{
        status = "completed"
        completedAt = (Get-Date).ToString("o")
        exitCode = 0
        archivePath = $backupPath
        suffix = $normalizedSuffix
        dbonly = $dbOnlyEnabled
        background = $runInBackground
        dbtype = "p"
        container = $pgContainer
        database = $pgDb
    }
    $metaPath = Write-BackupMeta -logsDir $logsDir -meta $meta
    Write-Output "ARCHIVE_PATH=$backupPath"
    Write-Output "META_PATH=$metaPath"
} else {
    Write-Host "docker cp failed with exit code $copyExitCode" -ForegroundColor Red
    $meta = @{
        status = "failed"
        failedAt = (Get-Date).ToString("o")
        exitCode = $copyExitCode
        archivePath = $backupPath
        suffix = $normalizedSuffix
        dbonly = $dbOnlyEnabled
        background = $runInBackground
        dbtype = "p"
        container = $pgContainer
        database = $pgDb
    }
    $metaPath = Write-BackupMeta -logsDir $logsDir -meta $meta
    Write-Output "META_PATH=$metaPath"
    throw "Failed to copy Postgres dump from container."
}
