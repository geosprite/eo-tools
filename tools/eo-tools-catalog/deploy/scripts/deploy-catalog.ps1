param(
    [string]$SshHost = "jsong@10.168.162.111",
    [string]$K3sNodeIp = "10.168.162.111",
    [string]$RegistryHost = "10.168.162.111:5000",
    [string]$ImageName = "eo-tools-catalog",
    [string]$ImageTag = "",
    [string]$RemoteDir = "/tmp/eo-tools-catalog-deploy",
    [switch]$NoBuild,
    [switch]$NoPush,
    [switch]$SkipRemote,
    [switch]$DryRun,
    [switch]$KeepRemoteDir
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-Step {
    param(
        [string]$Title,
        [scriptblock]$Body
    )
    Write-Host ""
    Write-Host "==> $Title"
    & $Body
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Require-Command docker
Require-Command scp
Require-Command ssh

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$eoRoot = Resolve-Path (Join-Path $scriptDir "..\..\..\..\..")
$dockerfile = Join-Path $eoRoot "eo-tools\tools\eo-tools-catalog\deploy\docker\Dockerfile"
$manifest = Join-Path $eoRoot "eo-tools\tools\eo-tools-catalog\deploy\k8s\eo-tools-catalog.yaml"
$remoteScript = Join-Path $eoRoot "eo-tools\tools\eo-tools-catalog\deploy\scripts\deploy-catalog-remote.sh"

if (-not $RegistryHost) {
    $RegistryHost = "${K3sNodeIp}:5000"
}

if (-not $ImageTag) {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        try {
            $ImageTag = (& git -C (Join-Path $eoRoot "eo-tools") rev-parse --short HEAD).Trim()
        } catch {
            $ImageTag = ""
        }
    }
    if (-not $ImageTag) {
        $ImageTag = Get-Date -Format "yyyyMMddHHmmss"
    }
}

$localImage = "${ImageName}:${ImageTag}"
$remoteImage = "${RegistryHost}/${ImageName}:${ImageTag}"
$renderedManifest = Join-Path $env:TEMP "eo-tools-catalog.$($ImageTag -replace '[^A-Za-z0-9_.-]', '_').yaml"

Write-Host "EO root:       $eoRoot"
Write-Host "SSH host:      $SshHost"
Write-Host "K3s node IP:   $K3sNodeIp"
Write-Host "Registry host: $RegistryHost"
Write-Host "Image:         $remoteImage"
Write-Host "Remote dir:    $RemoteDir"
Write-Host "Manifest:      $renderedManifest"

Invoke-Step "Render Kubernetes manifest" {
    if ($DryRun) {
        Write-Host "Render $manifest with image $remoteImage -> $renderedManifest"
    } else {
        $content = Get-Content -LiteralPath $manifest -Raw
        $pattern = "(?m)^(\s*image:\s*)(?:\S+/)?$([regex]::Escape($ImageName)):\S+\s*$"
        $rendered = [regex]::Replace(
            $content,
            $pattern,
            [System.Text.RegularExpressions.MatchEvaluator]{
                param($match)
                return "$($match.Groups[1].Value)$remoteImage"
            }
        )
        if ($rendered -eq $content) {
            throw "No image line for ${ImageName} was replaced in manifest: $manifest"
        }
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($renderedManifest, $rendered, $utf8NoBom)
    }
}

if (-not $NoBuild) {
    Invoke-Step "Build Docker image" {
        if ($DryRun) {
            Write-Host "docker build -t $localImage -f $dockerfile $eoRoot"
        } else {
            docker build `
                -t $localImage `
                -f $dockerfile `
                $eoRoot
        }
    }
}

Invoke-Step "Tag Docker image" {
    if ($DryRun) {
        Write-Host "docker tag $localImage $remoteImage"
    } else {
        docker tag $localImage $remoteImage
    }
}

if (-not $NoPush) {
    Invoke-Step "Push Docker image" {
        if ($DryRun) {
            Write-Host "docker push $remoteImage"
        } else {
            docker push $remoteImage
        }
    }
}

if (-not $SkipRemote) {
    Invoke-Step "Prepare remote deploy directory" {
        $remotePrepareCommand = "mkdir -p '$RemoteDir' && test -d '$RemoteDir' && test -w '$RemoteDir'"
        if ($DryRun) {
            Write-Host "ssh $SshHost `"$remotePrepareCommand`""
        } else {
            ssh $SshHost $remotePrepareCommand
            if ($LASTEXITCODE -ne 0) {
                throw "Remote directory is missing or not writable: ${SshHost}:${RemoteDir}. If it was created by root, run: sudo chown -R `$USER:`$USER '$RemoteDir'"
            }
        }
    }

    Invoke-Step "Copy manifest and remote deploy script" {
        if ($DryRun) {
            Write-Host "scp $renderedManifest ${SshHost}:${RemoteDir}/eo-tools-catalog.yaml"
            Write-Host "scp $remoteScript ${SshHost}:${RemoteDir}/deploy-catalog-remote.sh"
        } else {
            scp $renderedManifest "${SshHost}:${RemoteDir}/eo-tools-catalog.yaml"
            scp $remoteScript "${SshHost}:${RemoteDir}/deploy-catalog-remote.sh"
        }
    }

    Invoke-Step "Apply deployment on k3s" {
        $remoteCommand = "chmod +x '$RemoteDir/deploy-catalog-remote.sh' && '$RemoteDir/deploy-catalog-remote.sh' --image '$remoteImage' --node-ip '$K3sNodeIp' --manifest '$RemoteDir/eo-tools-catalog.yaml'"
        if ($DryRun) {
            Write-Host "ssh -tt $SshHost `"$remoteCommand`""
        } else {
            ssh -tt $SshHost $remoteCommand
        }
    }

    if (-not $KeepRemoteDir) {
        Invoke-Step "Clean remote deploy directory" {
            $remoteCleanupCommand = "rm -rf '$RemoteDir'"
            if ($DryRun) {
                Write-Host "ssh $SshHost `"$remoteCleanupCommand`""
            } else {
                ssh $SshHost $remoteCleanupCommand
            }
        }
    }
}

Write-Host ""
Write-Host "Deployment image: $remoteImage"
Write-Host "Expected URLs:"
Write-Host "  http://$K3sNodeIp/eo-tools/health"
Write-Host "  http://$K3sNodeIp/eo-tools/"
Write-Host "  http://$K3sNodeIp/eo-tools/docs"
