[CmdletBinding()]
param(
    [string]$Path = ".",
    [switch]$SkipContentScan
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path -LiteralPath $Path).Path
$ForbiddenDirectoryNames = @(
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "tf210_env",
    ".venv-docs",
    ".tmp_docs_deps",
    "tmp_docs_deps",
    ".ipynb_checkpoints",
    "node_modules",
    "runtime",
    "private_runtime",
    "mlruns",
    "outputs",
    "plots",
    "logs",
    "models",
    "notebooks",
    "production_predictions",
    "hydra_production_predictions",
    "site",
    "dist"
)
$ForbiddenFileNames = @(".env")
$ForbiddenExtensions = @(
    ".parquet",
    ".h5",
    ".keras",
    ".ckpt",
    ".onnx",
    ".joblib",
    ".pkl",
    ".pickle",
    ".pt",
    ".pth",
    ".pb",
    ".tflite",
    ".npy",
    ".npz",
    ".rds",
    ".xlsx",
    ".xls",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".zip",
    ".tar",
    ".gz",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".crt",
    ".cer"
)
$TextExtensions = @(
    ".ps1",
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".txt",
    ".md",
    ".example"
)

function Is-SyntheticExample {
    param([string]$FullName)

    $Normalized = $FullName.Replace("\", "/")
    return $Normalized -like "*/examples/*"
}

function Is-PublicSelectionFile {
    param([string]$FullName)

    $Normalized = $FullName.Replace("\", "/")
    return $Normalized -like "*/selections/*.csv"
}

function Is-PublicReferenceFile {
    param([string]$FullName)

    $Name = [System.IO.Path]::GetFileName($FullName)
    return $Name -in @("UPperRS.xlsx", "UPperRS.example.xlsx")
}

function Is-GitInternalPath {
    param([string]$FullName)

    $Normalized = $FullName.Replace("\", "/")
    return $Normalized -like "*/.git/*"
}

function Is-PublicPlaceholderValue {
    param([string]$Value)

    $Trimmed = $Value.Trim().Trim('"').Trim("'")
    if ([string]::IsNullOrWhiteSpace($Trimmed)) {
        return $true
    }

    return (
        $Trimmed -match '^(?i:true|false|null|none|read|write)$' -or
        $Trimmed -eq '(' -or
        $Trimmed -match '^\$\{.+\}$' -or
        $Trimmed -match '^\$\{\{.+\}\}$' -or
        $Trimmed -match '^<.+>$' -or
        $Trimmed -match '^(?i:os\.getenv|str|re\.sub|Path|pd\.|_build[A-Za-z0-9_]*)[\(\.]' -or
        $Trimmed -match '^[A-Za-z_][A-Za-z0-9_]*\.' -or
        $Trimmed -match '(?i)example|dummy|synthetic|changeme|change-me|placeholder|localhost|127\.0\.0\.1|predap|postgres|mlflow'
    )
}

$SensitiveKeyPattern = '[A-Za-z0-9_.-]*(?:password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|connection[_-]?string)[A-Za-z0-9_.-]*'
$SensitiveEqualsPattern = "(?i)^\s*($SensitiveKeyPattern)\s*(?::\s*[^=:#]+)?\s*=\s*([^#\s]+)"
$SensitiveYamlPattern = "(?i)^\s*($SensitiveKeyPattern)\s*:\s*([^#\s]+)"
$Problems = New-Object System.Collections.Generic.List[string]

Get-ChildItem -LiteralPath $Root -Recurse -Force -Directory | ForEach-Object {
    if (-not (Is-GitInternalPath $_.FullName)) {
        if ($ForbiddenDirectoryNames -contains $_.Name -and -not (Is-SyntheticExample $_.FullName)) {
            $Problems.Add("Forbidden directory: $($_.FullName)")
        }
        if ($_.Name -eq "data" -and -not (Is-SyntheticExample $_.FullName)) {
            $Problems.Add("Data directory outside synthetic examples: $($_.FullName)")
        }
    }
}

Get-ChildItem -LiteralPath $Root -Recurse -Force -File | ForEach-Object {
    $FileFullName = $_.FullName
    $FileName = $_.Name
    $FileLength = $_.Length
    $Extension = $_.Extension.ToLowerInvariant()

    if (-not (Is-GitInternalPath $FileFullName)) {
        if ($ForbiddenFileNames -contains $FileName) {
            $Problems.Add("Forbidden file: $FileFullName")
        }

        if ($FileName -like ".env*" -and $FileName -ne ".env.example") {
            $Problems.Add("Forbidden environment file: $FileFullName")
        }

        if ($ForbiddenExtensions -contains $Extension -and -not (Is-SyntheticExample $FileFullName) -and -not (Is-PublicReferenceFile $FileFullName)) {
            $Problems.Add("Forbidden artifact extension: $FileFullName")
        }

        if ($Extension -eq ".csv" -and -not (Is-SyntheticExample $FileFullName) -and -not (Is-PublicSelectionFile $FileFullName)) {
            $Problems.Add("CSV outside synthetic examples: $FileFullName")
        }

        if (-not $SkipContentScan -and ($TextExtensions -contains $Extension -or $FileName -eq ".env.example") -and $FileLength -lt 1MB) {
            $LineNumber = 0
            Get-Content -LiteralPath $FileFullName -ErrorAction Stop | ForEach-Object {
                $LineNumber += 1
                $Key = $null
                $Value = $null
                if ($_ -match $SensitiveEqualsPattern) {
                    $Key = $matches[1]
                    $Value = $matches[2]
                } elseif ($_ -match $SensitiveYamlPattern) {
                    $Key = $matches[1]
                    $Value = $matches[2]
                }

                if ($Key) {
                    $IsGitHubPermission = $Key -eq "id-token" -and $Value -match '^(read|write|none)$'
                    $IsPublicModelToken = $Key -match '(?i)(^|\.)covid[_-]?token(?:_list)?$'
                    if (-not $IsGitHubPermission -and -not $IsPublicModelToken -and -not (Is-PublicPlaceholderValue $Value)) {
                        $Problems.Add("Possible secret assignment: ${FileFullName}:$LineNumber")
                    }
                }
            }
        }
    }
}

if ($Problems.Count -gt 0) {
    $Problems | ForEach-Object { Write-Error $_ }
    throw "GitHub safety check failed with $($Problems.Count) problem(s)."
}

Write-Host "GitHub safety check passed for $Root"
