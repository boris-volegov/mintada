param(
    [Parameter(Mandatory = $true)]
    [string]$suffix,

    [string]$dbonly = "true",

    [string]$background = "false"
)

# Backup Data Script
# Archives the HTML folder and coins.db to a 7z file.

# Configuration
$sevenZipPath = "C:\Program Files\7-Zip\7z.exe"
$backupDir = "D:\bkp\numista_bkp"

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

$dbOnlyEnabled = ConvertTo-Bool -value $dbonly -name "dbonly"
$runInBackground = ConvertTo-Bool -value $background -name "background"

$normalizedSuffix = $suffix.Trim()
if ([string]::IsNullOrWhiteSpace($normalizedSuffix)) {
    throw "suffix cannot be empty."
}

# Allow passing with or without .7z
$normalizedSuffix = $normalizedSuffix -replace "\.7z$", ""
$datePart = Get-Date -Format "yyyy_MM_dd"
$backupFile = "numista_${datePart}_${normalizedSuffix}.7z"
$backupPath = Join-Path $backupDir $backupFile

$sourceHtml = "D:\projects\mintada\scrappers\numista\coin_types\html"
$sourceDb = "D:\projects\mintada\data\numista\coins.db"
$logsDir = Join-Path $backupDir "logs"

# 1. Check if 7-Zip exists
if (-not (Test-Path $sevenZipPath)) {
    throw "7-Zip not found at $sevenZipPath."
}

# 2. Ensure backup directory exists
if (-not (Test-Path $backupDir)) {
    Write-Host "Creating backup directory: $backupDir"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

# 3. Create Archive
Write-Host "Creating backup archive at: $backupPath" -ForegroundColor Cyan
Write-Host "Sources:"
Write-Host " - $sourceDb"
if (-not $dbOnlyEnabled) {
    Write-Host " - $sourceHtml"
}

# arguments: a (add), archive path, selected sources
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
    }
    $metaPath = Join-Path $logsDir "last_backup.json"
    $meta | ConvertTo-Json -Depth 5 | Set-Content -Path $metaPath -Encoding UTF8
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
    }
    $metaPath = Join-Path $logsDir "last_backup.json"
    $meta | ConvertTo-Json -Depth 5 | Set-Content -Path $metaPath -Encoding UTF8
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
    }
    $metaPath = Join-Path $logsDir "last_backup.json"
    $meta | ConvertTo-Json -Depth 5 | Set-Content -Path $metaPath -Encoding UTF8
    Write-Output "META_PATH=$metaPath"
}
