[CmdletBinding()]
param(
    [string]$ReposRoot = "dist\github-repos",
    [string]$RemoteBaseUrl = "",
    [string]$RemoteMapPath = "",
    [string]$RemoteName = "origin",
    [string]$Branch = "main",
    [string]$CommitMessage = "Initial PREDAP public release",
    [switch]$Push,
    [switch]$ForcePush,
    [switch]$ForceRemote,
    [switch]$SkipSafetyCheck,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ReposFull = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $ReposRoot))

if (-not (Test-Path -LiteralPath $ReposFull)) {
    throw "Repository export root does not exist: $ReposFull"
}

$RepoNames = @(
    "predap-platform",
    "predap-data-retrieval",
    "predap-cclr",
    "predap-training",
    "predap-inference",
    "prediction-analysis"
)

$RemoteMap = @{}
if ($RemoteMapPath) {
    $RemoteMapFull = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $RemoteMapPath))
    if (-not (Test-Path -LiteralPath $RemoteMapFull)) {
        throw "Remote map does not exist: $RemoteMapFull"
    }
    $RemoteMapJson = Get-Content -LiteralPath $RemoteMapFull -Raw | ConvertFrom-Json
    foreach ($Property in $RemoteMapJson.PSObject.Properties) {
        $RemoteMap[$Property.Name] = [string]$Property.Value
    }
}

if ($RemoteBaseUrl) {
    if ($RemoteBaseUrl -match '[\[\]\(\)]' -or $RemoteBaseUrl -match '<org>' -or $RemoteBaseUrl -match '<.+>') {
        throw "RemoteBaseUrl must be a plain GitHub owner URL such as https://github.com/guillemhg98, not a Markdown link or placeholder: $RemoteBaseUrl"
    }
}

function Invoke-Git {
    param([string[]]$GitArgs)

    & git @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "git $($GitArgs -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Test-GitHead {
    $PreviousErrorActionPreference = $ErrorActionPreference
    $HadNativeErrorPreference = Test-Path -LiteralPath "Variable:\PSNativeCommandUseErrorActionPreference"
    if ($HadNativeErrorPreference) {
        $PreviousNativeErrorPreference = $PSNativeCommandUseErrorActionPreference
    }

    try {
        $ErrorActionPreference = "Continue"
        if ($HadNativeErrorPreference) {
            $script:PSNativeCommandUseErrorActionPreference = $false
        }
        & git rev-parse --verify --quiet HEAD *> $null
        return $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
        if ($HadNativeErrorPreference) {
            $script:PSNativeCommandUseErrorActionPreference = $PreviousNativeErrorPreference
        }
    }
}

function Get-GitRemoteUrl {
    param([string]$Name)

    $PreviousErrorActionPreference = $ErrorActionPreference
    $HadNativeErrorPreference = Test-Path -LiteralPath "Variable:\PSNativeCommandUseErrorActionPreference"
    if ($HadNativeErrorPreference) {
        $PreviousNativeErrorPreference = $PSNativeCommandUseErrorActionPreference
    }

    try {
        $ErrorActionPreference = "Continue"
        if ($HadNativeErrorPreference) {
            $script:PSNativeCommandUseErrorActionPreference = $false
        }
        $RemoteUrl = & git remote get-url $Name 2>$null
        if ($LASTEXITCODE -eq 0) {
            return [pscustomobject]@{
                Exists = $true
                Url = [string]($RemoteUrl | Select-Object -First 1)
            }
        }
        return [pscustomobject]@{
            Exists = $false
            Url = ""
        }
    } finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
        if ($HadNativeErrorPreference) {
            $script:PSNativeCommandUseErrorActionPreference = $PreviousNativeErrorPreference
        }
    }
}

function Invoke-GitOptional {
    param([string[]]$GitArgs)

    $PreviousErrorActionPreference = $ErrorActionPreference
    $HadNativeErrorPreference = Test-Path -LiteralPath "Variable:\PSNativeCommandUseErrorActionPreference"
    if ($HadNativeErrorPreference) {
        $PreviousNativeErrorPreference = $PSNativeCommandUseErrorActionPreference
    }

    try {
        $ErrorActionPreference = "Continue"
        if ($HadNativeErrorPreference) {
            $script:PSNativeCommandUseErrorActionPreference = $false
        }
        & git @GitArgs
        return $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
        if ($HadNativeErrorPreference) {
            $script:PSNativeCommandUseErrorActionPreference = $PreviousNativeErrorPreference
        }
    }
}

function Get-TargetRemoteUrl {
    param([string]$RepoName)

    if ($RemoteMap.ContainsKey($RepoName)) {
        return $RemoteMap[$RepoName]
    }

    if ($RemoteBaseUrl) {
        return "$($RemoteBaseUrl.TrimEnd('/'))/$RepoName.git"
    }

    return ""
}

function Remove-PublishNoise {
    param([string]$RepoRoot)

    $NoiseDirectories = @(
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".ipynb_checkpoints",
        "runtime",
        "private_runtime",
        "site",
        "mlruns",
        "outputs",
        "plots",
        "logs",
        "models",
        "production_predictions",
        "hydra_production_predictions"
    )

    foreach ($NoiseName in $NoiseDirectories) {
        Get-ChildItem -LiteralPath $RepoRoot -Recurse -Force -Directory -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -eq $NoiseName
        } | ForEach-Object {
            $FullName = [System.IO.Path]::GetFullPath($_.FullName)
            if (-not $FullName.StartsWith($RepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Refusing to remove publish-noise path outside repository: $FullName"
            }
            Remove-Item -LiteralPath $FullName -Recurse -Force
        }
    }

    Get-ChildItem -LiteralPath $RepoRoot -Recurse -Force -File -ErrorAction SilentlyContinue | Where-Object {
        $_.Extension.ToLowerInvariant() -in @(".pyc", ".pyo")
    } | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Force
    }
}

foreach ($RepoName in $RepoNames) {
    $RepoPath = Join-Path $ReposFull $RepoName
    if (Test-Path -LiteralPath $RepoPath) {
        Remove-PublishNoise -RepoRoot ([System.IO.Path]::GetFullPath($RepoPath))
    }
}

if (-not $SkipSafetyCheck) {
    $SafetyScript = Join-Path $ProjectRoot "scripts\check_github_safety.ps1"
    if (-not (Test-Path -LiteralPath $SafetyScript)) {
        throw "Missing safety script: $SafetyScript"
    }

    Write-Host "Running GitHub safety check for $ReposFull"
    & $SafetyScript -Path $ReposFull
}

foreach ($RepoName in $RepoNames) {
    $RepoPath = Join-Path $ReposFull $RepoName
    if (-not (Test-Path -LiteralPath $RepoPath)) {
        throw "Expected exported repository is missing: $RepoPath"
    }

    $TargetRemoteUrl = Get-TargetRemoteUrl -RepoName $RepoName
    Write-Host ""
    Write-Host "Repository: $RepoName"
    Write-Host "Path:       $RepoPath"
    if ($TargetRemoteUrl) {
        Write-Host "Remote:     $TargetRemoteUrl"
    } else {
        Write-Host "Remote:     unchanged"
    }

    if ($DryRun) {
        Write-Host "Dry run: would init, stage, commit if needed, set branch $Branch, configure remote when provided, and push only if -Push is set."
        if ($ForcePush) {
            Write-Host "Dry run: push would use --force-with-lease because -ForcePush is set."
        }
        continue
    }

    Push-Location $RepoPath
    try {
        if (-not (Test-Path -LiteralPath ".git")) {
            Invoke-Git -GitArgs @("init")
        }

        Invoke-Git -GitArgs @("add", ".")

        $HasHead = Test-GitHead

        $Status = & git status --porcelain
        if ($LASTEXITCODE -ne 0) {
            throw "git status --porcelain failed with exit code $LASTEXITCODE"
        }

        if ((-not $HasHead) -or $Status) {
            Invoke-Git -GitArgs @("commit", "-m", $CommitMessage)
        } else {
            Write-Host "No changes to commit."
        }

        Invoke-Git -GitArgs @("branch", "-M", $Branch)

        if ($TargetRemoteUrl) {
            $RemoteInfo = Get-GitRemoteUrl -Name $RemoteName

            if ($RemoteInfo.Exists) {
                if ($RemoteInfo.Url -ne $TargetRemoteUrl) {
                    if ($ForceRemote) {
                        Invoke-Git -GitArgs @("remote", "set-url", $RemoteName, $TargetRemoteUrl)
                    } else {
                        throw "Remote $RemoteName already points to $($RemoteInfo.Url). Re-run with -ForceRemote to replace it."
                    }
                }
            } else {
                Invoke-Git -GitArgs @("remote", "add", $RemoteName, $TargetRemoteUrl)
            }
        }

        $PushRemoteInfo = Get-GitRemoteUrl -Name $RemoteName
        if ($Push) {
            if (-not $PushRemoteInfo.Exists) {
                throw "Cannot push $RepoName because remote $RemoteName is not configured."
            }
            $PushArgs = @("push", "-u", $RemoteName, $Branch)
            if ($ForcePush) {
                Invoke-GitOptional -GitArgs @("fetch", $RemoteName, $Branch) | Out-Null
                $PushArgs = @("push", "--force-with-lease", "-u", $RemoteName, $Branch)
            }
            Invoke-Git -GitArgs $PushArgs
        }
    } finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Done."
