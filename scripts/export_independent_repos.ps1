[CmdletBinding()]
param(
    [string]$OutputRoot = "dist\github-repos",
    [switch]$InitGit,
    [switch]$RunSafetyCheck,
    [switch]$Force,
    [switch]$AllowMissingPaths
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$OutputFull = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $OutputRoot))

if (-not $OutputFull.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputRoot must stay inside the project root: $OutputFull"
}

function Reset-RepoDir {
    param([string]$RepoPath)

    if (Test-Path -LiteralPath $RepoPath) {
        if (-not $Force) {
            throw "Target already exists: $RepoPath. Re-run with -Force to replace it."
        }
        $FullRepoPath = [System.IO.Path]::GetFullPath($RepoPath)
        if (-not $FullRepoPath.StartsWith($OutputFull, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove path outside export root: $FullRepoPath"
        }
        Remove-Item -LiteralPath $FullRepoPath -Recurse -Force
    }

    New-Item -ItemType Directory -Path $RepoPath -Force | Out-Null
}

function Copy-RelativePath {
    param(
        [string]$SourceRel,
        [string]$DestRoot,
        [string]$DestRel = $SourceRel
    )

    $Source = Join-Path $ProjectRoot $SourceRel
    if (-not (Test-Path -LiteralPath $Source)) {
        if ($AllowMissingPaths) {
            Write-Warning "Skipping missing path: $SourceRel"
            return
        }
        throw "Missing required export path: $SourceRel. Run the export from the complete source workspace, or re-run with -AllowMissingPaths only for an intentional partial export."
        return
    }

    $Destination = Join-Path $DestRoot $DestRel
    $Parent = Split-Path -Parent $Destination
    if ($Parent) {
        New-Item -ItemType Directory -Path $Parent -Force | Out-Null
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
}

function Copy-CommonSyntheticExample {
    param([string]$DestRoot)

    Copy-RelativePath -SourceRel "examples\synthetic" -DestRoot $DestRoot -DestRel "examples\synthetic"
}

function Remove-ExportNoise {
    param([string]$RepoRoot)

    $NoiseDirectories = @(
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".ipynb_checkpoints"
    )
    Get-ChildItem -LiteralPath $RepoRoot -Recurse -Force -Directory | Where-Object {
        $NoiseDirectories -contains $_.Name
    } | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
    }

    Get-ChildItem -LiteralPath $RepoRoot -Recurse -Force -File | Where-Object {
        $_.Extension -in @(".pyc", ".pyo")
    } | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Force
    }
}

New-Item -ItemType Directory -Path $OutputFull -Force | Out-Null

$CommonRepositoryFiles = @(
    "LICENSE",
    "SECURITY.md",
    "SUPPORT.md",
    "DATA_POLICY.md",
    "CONTRIBUTING.md",
    ".gitattributes",
    @{ Source = "scripts\check_github_safety.ps1"; Dest = "scripts\check_github_safety.ps1" },
    @{ Source = "scripts\create_private_runtime_skeleton.ps1"; Dest = "scripts\create_private_runtime_skeleton.ps1" }
)

$Repos = @(
    @{
        Name = "predap-platform"
        Paths = @(
            "README.md",
            "PREDAP_PLATFORM.yml",
            ".env.example",
            ".gitignore",
            "docker-compose.yml",
            "dockerfile",
            "docs",
            "docs-requirements.txt",
            "mkdocs.yml",
            ".github",
            "scripts\export_independent_repos.ps1",
            "scripts\publish_independent_repos.ps1",
            "scripts\check_private_runtime_contract.py",
            "scripts\validate_synthetic_outputs.py",
            "scripts\log_inference_outputs_to_mlflow.py",
            "scripts\run_daily_inference_to_mlflow.py"
        )
        Synthetic = $true
    },
    @{
        Name = "predap-data-retrieval"
        Paths = @(
            "AQUAS_DATA_RETRIEVAL-git\README.md",
            "AQUAS_DATA_RETRIEVAL-git\.env.example",
            "AQUAS_DATA_RETRIEVAL-git\.gitignore",
            "AQUAS_DATA_RETRIEVAL-git\mkdocs.yml",
            "AQUAS_DATA_RETRIEVAL-git\requirements.txt",
            "AQUAS_DATA_RETRIEVAL-git\setup.py",
            "AQUAS_DATA_RETRIEVAL-git\UPperRS.xlsx",
            "AQUAS_DATA_RETRIEVAL-git\UPperRS.example.xlsx",
            "AQUAS_DATA_RETRIEVAL-git\run_pipeline.py",
            "AQUAS_DATA_RETRIEVAL-git\run_pipeline_optimized.py",
            "AQUAS_DATA_RETRIEVAL-git\validate_project.py",
            "AQUAS_DATA_RETRIEVAL-git\.github",
            "AQUAS_DATA_RETRIEVAL-git\config",
            "AQUAS_DATA_RETRIEVAL-git\docs",
            "AQUAS_DATA_RETRIEVAL-git\examples\retrieval_sample",
            "AQUAS_DATA_RETRIEVAL-git\pipelines",
            "AQUAS_DATA_RETRIEVAL-git\scripts\check_source_upload_metadata.py",
            "AQUAS_DATA_RETRIEVAL-git\scripts\create_multiyear_sample.py",
            "AQUAS_DATA_RETRIEVAL-git\scripts\export_contract_outputs.py",
            "AQUAS_DATA_RETRIEVAL-git\selections",
            "AQUAS_DATA_RETRIEVAL-git\tests",
            "AQUAS_DATA_RETRIEVAL-git\src"
        )
        Synthetic = $true
    },
    @{
        Name = "predap-cclr"
        Paths = @(
            "CCLR_PREDAP\README.md",
            "CCLR_PREDAP\.gitignore",
            "CCLR_PREDAP\LICENSE",
            "CCLR_PREDAP\requirements.txt",
            "CCLR_PREDAP\mkdocs.yml",
            "CCLR_PREDAP\.github",
            "CCLR_PREDAP\docs",
            "CCLR_PREDAP\src",
            "CCLR_PREDAP\main.py",
            "CCLR_PREDAP\main_LMLR.py",
            "CCLR_PREDAP\main_Gcausal.py",
            "CCLR_PREDAP\main_DL.py"
        )
        Synthetic = $true
    },
    @{
        Name = "predap-training"
        Paths = @(
            ".env.example",
            ".gitignore",
            "requirements.txt",
            "requirements-training-local.txt",
            "docker-compose.yml",
            "dockerfile",
            "conf",
            "src",
            "main_train.py",
            "main_train_quantization.py",
            "production\__init__.py",
            "production\model_quantization_pipeline.py",
            "production\data_preparation_in_poduction.py",
            @{ Source = "CCLR_PREDAP\README.md"; Dest = "predap-cclr\README.md" },
            @{ Source = "CCLR_PREDAP\LICENSE"; Dest = "predap-cclr\LICENSE" },
            @{ Source = "CCLR_PREDAP\requirements.txt"; Dest = "predap-cclr\requirements.txt" },
            @{ Source = "CCLR_PREDAP\main.py"; Dest = "predap-cclr\main.py" },
            @{ Source = "CCLR_PREDAP\main_DL.py"; Dest = "predap-cclr\main_DL.py" },
            @{ Source = "CCLR_PREDAP\main_Gcausal.py"; Dest = "predap-cclr\main_Gcausal.py" },
            @{ Source = "CCLR_PREDAP\main_LMLR.py"; Dest = "predap-cclr\main_LMLR.py" },
            @{ Source = "CCLR_PREDAP\src"; Dest = "predap-cclr\src" },
            "training_execution.sh",
            "scripts\train_all_codes.py",
            "scripts\preflight_training.py",
            "scripts\check_private_runtime_contract.py",
            "scripts\import_recovered_models_to_mlflow.py",
            "scripts\log_inference_outputs_to_mlflow.py",
            "scripts\run_daily_inference_to_mlflow.py",
            "scripts\mlflow_artifact_smoke.py",
            "scripts\migrate_mlflow_sqlite_to_postgres.py",
            "docs\repo-readmes\predap-training.md",
            @{ Source = "docs\repo-packages\predap-training\mkdocs.yml"; Dest = "mkdocs.yml" },
            @{ Source = "docs\repo-packages\predap-training\docs"; Dest = "docs" },
            @{ Source = "docs\repo-packages\predap-training\.github"; Dest = ".github" }
        )
        Synthetic = $true
        ReadmeSource = "docs\repo-readmes\predap-training.md"
    },
    @{
        Name = "predap-inference"
        Paths = @(
            "PREDAP_INFERENCE\README.md",
            "PREDAP_INFERENCE\.gitignore",
            "PREDAP_INFERENCE\mkdocs.yml",
            "PREDAP_INFERENCE\requirements.txt",
            "PREDAP_INFERENCE\Dockerfile",
            "PREDAP_INFERENCE\.github",
            "PREDAP_INFERENCE\docs",
            "PREDAP_INFERENCE\config",
            "PREDAP_INFERENCE\data_utils",
            "PREDAP_INFERENCE\model_architechture",
            "PREDAP_INFERENCE\production",
            "PREDAP_INFERENCE\residual_multivariate_transformers",
            "PREDAP_INFERENCE\univariate_transformer",
            "PREDAP_INFERENCE\utils",
            "scripts\log_inference_outputs_to_mlflow.py",
            "scripts\run_daily_inference_to_mlflow.py"
        )
        Synthetic = $true
    },
    @{
        Name = "prediction-analysis"
        Paths = @(
            "prediction-analysis\README.md",
            "prediction-analysis\.gitignore",
            "prediction-analysis\pyproject.toml",
            "prediction-analysis\src",
            "prediction-analysis\tests"
        )
        Synthetic = $false
    }
)

foreach ($Repo in $Repos) {
    $RepoRoot = Join-Path $OutputFull $Repo.Name
    Reset-RepoDir -RepoPath $RepoRoot

    foreach ($CommonPath in $CommonRepositoryFiles) {
        $SourcePath = $CommonPath
        $DestOverride = $null
        if ($CommonPath -is [System.Collections.IDictionary]) {
            $SourcePath = $CommonPath.Source
            $DestOverride = $CommonPath.Dest
        }
        $DestRel = if ($DestOverride) { $DestOverride } else { $SourcePath }
        Copy-RelativePath -SourceRel $SourcePath -DestRoot $RepoRoot -DestRel $DestRel
    }

    foreach ($Path in $Repo.Paths) {
        $SourcePath = $Path
        $DestOverride = $null
        if ($Path -is [System.Collections.IDictionary]) {
            $SourcePath = $Path.Source
            $DestOverride = $Path.Dest
        }

        if ($Repo.ContainsKey("ReadmeSource") -and $SourcePath -eq $Repo.ReadmeSource) {
            Copy-RelativePath -SourceRel $SourcePath -DestRoot $RepoRoot -DestRel "README.md"
        } else {
            $DestRel = $SourcePath
            if ($DestOverride) {
                $DestRel = $DestOverride
            } elseif ($SourcePath.StartsWith("AQUAS_DATA_RETRIEVAL-git\")) {
                $DestRel = $SourcePath.Substring("AQUAS_DATA_RETRIEVAL-git\".Length)
            } elseif ($SourcePath.StartsWith("CCLR_PREDAP\")) {
                $DestRel = $SourcePath.Substring("CCLR_PREDAP\".Length)
            } elseif ($SourcePath.StartsWith("PREDAP_INFERENCE\")) {
                $DestRel = $SourcePath.Substring("PREDAP_INFERENCE\".Length)
            } elseif ($SourcePath.StartsWith("prediction-analysis\")) {
                $DestRel = $SourcePath.Substring("prediction-analysis\".Length)
            }
            Copy-RelativePath -SourceRel $SourcePath -DestRoot $RepoRoot -DestRel $DestRel
        }
    }

    if ($Repo.Synthetic) {
        Copy-CommonSyntheticExample -DestRoot $RepoRoot
    }

    if ($InitGit) {
        Push-Location $RepoRoot
        try {
            git init | Out-Null
        } finally {
            Pop-Location
        }
    }

    Remove-ExportNoise -RepoRoot $RepoRoot
    Write-Host "Exported $($Repo.Name) -> $RepoRoot"
}

if ($RunSafetyCheck) {
    & (Join-Path $ProjectRoot "scripts\check_github_safety.ps1") -Path $OutputFull
    Write-Host "Done. GitHub safety check passed for $OutputFull."
} else {
    Write-Host "Done. Run scripts\check_github_safety.ps1 against $OutputFull before publishing."
}
