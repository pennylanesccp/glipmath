param(
    [int]$Port = 8501,
    [switch]$Headless,
    [switch]$NoBrowser,
    [switch]$ForceInstall,
    [switch]$SkipAuthRedirectGuard
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

function Get-AuthRedirectUriFromSecrets {
    param(
        [string]$SecretsPath
    )

    if (-not (Test-Path $SecretsPath)) {
        return $null
    }

    $inAuthSection = $false
    foreach ($line in Get-Content $SecretsPath) {
        $trimmed = $line.Trim()

        if ($trimmed -match '^\[(.+)\]$') {
            $inAuthSection = $Matches[1] -eq "auth"
            continue
        }

        if (-not $inAuthSection -or [string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
            continue
        }

        if ($trimmed -match '^redirect_uri\s*=\s*"([^"]+)"') {
            return $Matches[1]
        }
    }

    return $null
}

function Test-IsSupportedLocalRedirectUri {
    param(
        [string]$RedirectUri,
        [int]$Port
    )

    if ([string]::IsNullOrWhiteSpace($RedirectUri)) {
        return $false
    }

    $normalized = $RedirectUri.Trim().ToLowerInvariant()
    $supportedUris = @(
        "http://localhost:$Port/oauth2callback",
        "http://127.0.0.1:$Port/oauth2callback",
        "http://localhost:{port}/oauth2callback",
        "http://127.0.0.1:{port}/oauth2callback"
    )

    return $supportedUris -contains $normalized
}

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
} elseif (-not $SkipAuthRedirectGuard) {
    $authRedirectUri = Get-AuthRedirectUriFromSecrets -SecretsPath $LocalSecretsPath
    if (-not (Test-IsSupportedLocalRedirectUri -RedirectUri $authRedirectUri -Port $Port)) {
        throw (
            "Local auth redirect_uri is incompatible with this Streamlit run. " +
            "Found '$authRedirectUri' in '$LocalSecretsPath'. " +
            "For local runs, use 'http://localhost:$Port/oauth2callback' " +
            "or 'http://localhost:{port}/oauth2callback'. " +
            "Keep the published Streamlit Community Cloud callback only in the deployed app secrets. " +
            "Use -SkipAuthRedirectGuard only if you intentionally want to bypass this local safety check."
        )
    }
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

