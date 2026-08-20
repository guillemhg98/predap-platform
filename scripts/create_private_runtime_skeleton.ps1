[CmdletBinding()]
param(
    [ValidateSet("platform", "data-retrieval", "cclr", "training", "inference", "analysis", "all")]
    [string]$Profile = "platform",
    [string]$Root = "."
)

$ErrorActionPreference = "Stop"

$RootFull = [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path $Root))
New-Item -ItemType Directory -Path $RootFull -Force | Out-Null

$Profiles = @{
    "data-retrieval" = @(
        "private_runtime\raw",
        "private_runtime\data",
        "private_runtime\reference",
        "private_runtime\data_retrieval_work",
        "private_runtime\logs"
    )
    "cclr" = @(
        "private_runtime\data",
        "private_runtime\best_features",
        "private_runtime\outputs"
    )
    "training" = @(
        "private_runtime\data",
        "private_runtime\best_features",
        "private_runtime\quantized_models",
        "private_runtime\models_parameters",
        "private_runtime\transformer_outputs",
        "private_runtime\history",
        "private_runtime\results",
        "private_runtime\production_predictions",
        "private_runtime\cclr_repo",
        "runtime\mlflow"
    )
    "inference" = @(
        "private_runtime\data",
        "private_runtime\best_features",
        "private_runtime\quantized_models",
        "private_runtime\results",
        "private_runtime\production_predictions",
        "private_runtime\production_predictions\real",
        "private_runtime\production_predictions\smoke"
    )
    "analysis" = @(
        "private_runtime\data",
        "private_runtime\production_predictions",
        "private_runtime\production_predictions\real",
        "private_runtime\analysis",
        "private_runtime\analysis\latest"
    )
}

$Profiles["platform"] = @(
    $Profiles["data-retrieval"] +
    $Profiles["cclr"] +
    $Profiles["training"] +
    $Profiles["inference"] +
    $Profiles["analysis"] +
    @("private_runtime\production_predictions\daily")
) | ForEach-Object { $_ } | Select-Object -Unique

$Profiles["all"] = $Profiles["platform"]

foreach ($RelativePath in $Profiles[$Profile]) {
    New-Item -ItemType Directory -Path (Join-Path $RootFull $RelativePath) -Force | Out-Null
}

Write-Host "Created private runtime skeleton for profile '$Profile' under $RootFull"
Write-Host "These folders are intentionally ignored by Git. Put real data and artifacts there after cloning."
