param(
    [int]$Port = 8501,
    [switch]$Headless,
    [switch]$NoBrowser,
    [switch]$ForceInstall
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppPath = Join-Path $RepoRoot "app\streamlit_app.py"
$VenvPath = Join-Path $RepoRoot "venv"
$VenvActivate = Join-Path $RepoRoot "venv\Scripts\Activate.ps1"
$VenvPython = Join-Path $RepoRoot "venv\Scripts\python.exe"
$VenvStreamlit = Join-Path $RepoRoot "venv\Scripts\streamlit.exe"
$EditableInstallMarker = Join-Path $RepoRoot "venv\.glipmath-editable.stamp"
$EditableInstallInputs = @(
    (Join-Path $RepoRoot "pyproject.toml"),
    (Join-Path $RepoRoot "requirements.txt")
)
$LocalSecretsPath = Join-Path $RepoRoot ".streamlit\secrets.toml"

if (-not (Test-Path $AppPath)) {
    throw "Streamlit app not found. Expected '$AppPath'."
}

$streamlitArgs = @(
    "run"
    $AppPath
    "--server.address"
    "0.0.0.0"
    "--server.port"
    "$Port"
)

if ($Headless -or $NoBrowser) {
    $streamlitArgs += @("--server.headless", "true")
} else {
    $streamlitArgs += @("--server.headless", "false")
}

if ($NoBrowser) {
    $streamlitArgs += @("--browser.gatherUsageStats", "false")
}

if (-not (Test-Path $VenvPath)) {
    throw "Virtual environment not found at '$VenvPath'. Create it first: python -m venv venv"
}

if (-not (Test-Path $VenvPython)) {
    throw "Python executable not found at '$VenvPython'."
}

Write-Host "Launching GlipMath Streamlit app: $AppPath"
Write-Host "Port: $Port"

if (-not (Test-Path $LocalSecretsPath)) {
    Write-Warning "Local secrets file not found at '$LocalSecretsPath'. Google auth and BigQuery access may fail."
}

Push-Location $RepoRoot
try {
    if (Test-Path $VenvActivate) {
        . $VenvActivate
    }

    $NeedsEditableInstall = $ForceInstall -or (-not (Test-Path $EditableInstallMarker))
    if (-not $NeedsEditableInstall) {
        $MarkerTime = (Get-Item $EditableInstallMarker).LastWriteTimeUtc
        foreach ($InputPath in $EditableInstallInputs) {
            if ((Test-Path $InputPath) -and ((Get-Item $InputPath).LastWriteTimeUtc -gt $MarkerTime)) {
                $NeedsEditableInstall = $true
                break
            }
        }
    }

    if ($NeedsEditableInstall) {
        Write-Host "Installing project in editable mode..."
        & $VenvPython -m pip install -e .
        Set-Content -Path $EditableInstallMarker -Value (Get-Date -Format o) -Encoding ascii
    } else {
        Write-Host "Skipping editable install (metadata unchanged). Use -ForceInstall to reinstall."
    }

    if (Test-Path $VenvStreamlit) {
        & $VenvStreamlit @streamlitArgs
    } else {
        & $VenvPython -m streamlit @streamlitArgs
    }
} finally {
    Pop-Location
}

