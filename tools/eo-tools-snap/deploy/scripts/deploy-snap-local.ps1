param(
    [string]$ImageName = "eo-tools-snap",
    [string]$ImageTag = "0.1.0",
    [int]$Port = 8000,
    [switch]$NoBuild,
    [switch]$Pull,
    [switch]$Down,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Test-DockerComposePlugin {
    try {
        & docker compose version *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Invoke-Compose {
    param([string[]]$Args)
    if ($script:UseDockerComposePlugin) {
        & docker compose @Args
    } else {
        & docker-compose @Args
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose command failed with exit code $LASTEXITCODE"
    }
}

$UseDockerComposePlugin = Test-DockerComposePlugin
if (-not $UseDockerComposePlugin) {
    Require-Command docker-compose
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$deployDir = Resolve-Path (Join-Path $scriptDir "..")
$composeFile = Join-Path $deployDir "docker-compose.yml"
$image = "${ImageName}:${ImageTag}"

Write-Host "Deploy dir: $deployDir"
Write-Host "Image:      $image"
Write-Host "Port:       $Port"
Write-Host "Compose:    $(if ($UseDockerComposePlugin) { 'docker compose' } else { 'docker-compose' })"

$env:EO_TOOLS_SNAP_IMAGE = $image
$env:EO_TOOLS_SNAP_PORT = [string]$Port

if ($Down) {
    if ($DryRun) {
        Write-Host "$(if ($UseDockerComposePlugin) { 'docker compose' } else { 'docker-compose' }) -f $composeFile down"
    } else {
        Invoke-Compose @("-f", $composeFile, "down")
    }
    exit 0
}

$composeArgs = @("-f", $composeFile, "up", "-d")
if (-not $NoBuild) {
    $composeArgs += "--build"
}
if ($Pull) {
    $composeArgs += "--pull"
    $composeArgs += "always"
}

if ($DryRun) {
    Write-Host "$(if ($UseDockerComposePlugin) { 'docker compose' } else { 'docker-compose' }) $($composeArgs -join ' ')"
} else {
    Invoke-Compose $composeArgs
    $healthUrl = "http://127.0.0.1:${Port}/snap/health"
    Write-Host "Waiting for $healthUrl"
    for ($i = 1; $i -le 60; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                Write-Host "Health OK: $healthUrl"
                Write-Host "Docs:      http://127.0.0.1:${Port}/snap/docs"
                exit 0
            }
        } catch {
            Start-Sleep -Seconds 5
        }
    }
    throw "eo-tools-snap did not become healthy at $healthUrl"
}
