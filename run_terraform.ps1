param(
    [ValidateSet("apply", "plan", "destroy", "output", "validate", "init")]
    [string]$Command = "apply",
    [string]$Environment = "dev",
    [switch]$AutoApprove,
    [switch]$Upgrade
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvironmentPath = Join-Path $RepoRoot "infrastructure\terraform\environments\$Environment"
$TerraformTfvarsPath = Join-Path $EnvironmentPath "terraform.tfvars"
$TerraformTfvarsExamplePath = Join-Path $EnvironmentPath "terraform.tfvars.example"

if (-not (Test-Path $EnvironmentPath)) {
    throw "Terraform environment not found. Expected '$EnvironmentPath'."
}

if ($null -eq (Get-Command terraform -ErrorAction SilentlyContinue)) {
    throw "Terraform executable not found in PATH. Install Terraform first."
}

function Invoke-Terraform {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & terraform @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Terraform command failed: terraform $($Arguments -join ' ')"
    }
}

function Add-TfvarsIfPresent {
    param(
        [Parameter(Mandatory = $true)]
        [ref]$Arguments
    )

    if (Test-Path $TerraformTfvarsPath) {
        $Arguments.Value += @("-var-file", $TerraformTfvarsPath)
        return
    }

    if (Test-Path $TerraformTfvarsExamplePath) {
        Write-Warning (
            "No terraform.tfvars found at '$TerraformTfvarsPath'. " +
            "Terraform will use defaults from variables.tf. " +
            "Copy '$TerraformTfvarsExamplePath' if you want explicit local values."
        )
    }
}

Write-Host "Running Terraform in: $EnvironmentPath"
Write-Host "Command: $Command"

Push-Location $EnvironmentPath
try {
    $initArgs = @("init")
    if ($Upgrade) {
        $initArgs += "-upgrade"
    }

    Invoke-Terraform -Arguments $initArgs

    if ($Command -eq "init") {
        return
    }

    $commandArgs = @($Command)
    if ($Command -in @("plan", "apply", "destroy")) {
        Add-TfvarsIfPresent -Arguments ([ref]$commandArgs)
    }
    if ($AutoApprove -and $Command -in @("apply", "destroy")) {
        $commandArgs += "-auto-approve"
    }

    Invoke-Terraform -Arguments $commandArgs
} finally {
    Pop-Location
}
