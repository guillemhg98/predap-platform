# From GitHub Clone to Public Repositories

This tutorial is the copy-paste path for a new user starting from GitHub. It
shows how to validate the public toy workflow, prepare the private real-data
workflow, inspect MLflow, and publish the split repositories safely.

For the most linear operator path, use
[Practical Runbook](practical-runbook.md). This page keeps the GitHub publishing
checklist in more detail.

## 0. Prerequisites

Install these tools before starting:

- Git;
- Python 3.10, 3.11 or 3.12 for local installs that include TensorFlow;
- Docker Desktop with Docker Compose;
- PowerShell;
- optional: GitHub CLI `gh`.

The public toy workflow and documentation build do not import TensorFlow, so
they can run on a newer Python if dependencies are already installed. Real
training, quantization and production-style inference should use Docker or a
Python 3.10-3.12 virtual environment. Python 3.13 cannot install the currently
supported local `tensorflow-cpu<2.18,>=2.16` dependency.

Choose one workspace mode.

**Option A: complete source workspace.** Use this when you have the full local
bundle that contains `docker-compose.yml`, `src/`, `PREDAP_INFERENCE/`,
`CCLR_PREDAP/` and `AQUAS_DATA_RETRIEVAL-git/` in one folder:

```powershell
cd C:\path\to\TRANSFORMERS_PREDAP_lite_autocontingut
$SourceRoot = (Get-Location).Path
$PlatformRepo = $SourceRoot
$TrainingRepo = $SourceRoot
$InferenceRepo = Join-Path $SourceRoot "PREDAP_INFERENCE"
```

**Option B: independent GitHub repositories.** Clone all repos into one parent
folder:

```powershell
mkdir predap-workspace
cd predap-workspace

git clone https://github.com/<org>/predap-platform.git
git clone https://github.com/<org>/predap-data-retrieval.git
git clone https://github.com/<org>/predap-cclr.git
git clone https://github.com/<org>/predap-training.git
git clone https://github.com/<org>/predap-inference.git
git clone https://github.com/<org>/prediction-analysis.git

$Workspace = (Get-Location).Path
$PlatformRepo = Join-Path $Workspace "predap-platform"
$TrainingRepo = Join-Path $Workspace "predap-training"
$InferenceRepo = Join-Path $Workspace "predap-inference"
$AnalysisRepo = Join-Path $Workspace "prediction-analysis"
```

Toy validation can run from the platform repo plus the inference repo. Real
training runs from the training repo. Real inference runs from the inference
repo while mounting the private training artifacts.

## 1. Public Toy Workflow

The toy workflow uses only synthetic data and dummy models. It is safe to run
from a public GitHub clone.

```powershell
Set-Location $PlatformRepo
python examples\synthetic\predap_synthetic_workflow.py --output-dir runtime\synthetic_demo
```

Inspect what was generated:

```powershell
Get-ChildItem runtime\synthetic_demo -Recurse
Get-Content runtime\synthetic_demo\retrieval_export\historical_daily.csv -TotalCount 5
Get-Content runtime\synthetic_demo\retrieval_export\target_codes_models_columns_order.json
Get-Content runtime\synthetic_demo\model_bundle\manifest.json
Get-Content runtime\synthetic_demo\inference\predictions.csv -TotalCount 10
Get-Content runtime\synthetic_demo\metrics.json
```

Validate the dummy model bundle:

```powershell
python "$InferenceRepo\production\validate_model_bundle.py" `
  --model-folder "$PlatformRepo\runtime\synthetic_demo\model_bundle"
```

Validate the platform-local synthetic outputs:

```powershell
python scripts\validate_synthetic_outputs.py --output-dir runtime\synthetic_demo
```

Expected result:

- `contains_real_data` is `false`;
- the manifest lists the synthetic target codes;
- each target code has dummy model files;
- `predictions.csv` has the production prediction columns.

The toy workflow does not create MLflow runs. It validates file contracts and
handoffs only.

## 2. Documentation Check

Install documentation dependencies:

```powershell
Set-Location $PlatformRepo
python -m venv .venv-docs
.\.venv-docs\Scripts\python.exe -m pip install --upgrade pip
.\.venv-docs\Scripts\python.exe -m pip install -r docs-requirements.txt
```

Build the docs strictly:

```powershell
.\.venv-docs\Scripts\python.exe -m mkdocs build --strict --site-dir runtime\docs_check
```

Serve the docs locally:

```powershell
.\.venv-docs\Scripts\python.exe -m mkdocs serve
```

Open:

```text
http://127.0.0.1:8000
```

## 3. Prepare Private Real Data

Real data must stay outside Git. Create the ignored private runtime layout:

```powershell
Set-Location $TrainingRepo
New-Item -ItemType Directory -Force `
  private_runtime\data, `
  private_runtime\best_features, `
  private_runtime\quantized_models, `
  private_runtime\models_parameters, `
  private_runtime\transformer_outputs, `
  private_runtime\history, `
  private_runtime\results, `
  private_runtime\production_predictions, `
  private_runtime\production_predictions\real, `
  private_runtime\production_predictions\smoke, `
  runtime\mlflow
```

Place real private inputs here:

```text
private_runtime\data\historical_daily.parquet
private_runtime\data\historical_daily.csv
private_runtime\data\target_codes_models_columns_order.json
private_runtime\best_features\BEST_features_NOSMOOTH_<CODE>.xlsx
```

Minimum table contract:

```text
timestamp,<CODE_1>,<CODE_2>,...
2024-01-01,123,45,...
```

Minimum target-code JSON:

```json
[
  "DEMAND__TOTAL",
  "SERVEI_CODI__URG"
]
```

## 4. Configure Real-Data Paths

Create a local `.env` from the template:

```powershell
Set-Location $TrainingRepo
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

Make sure `.env` contains these private path values:

```text
HOST_RUNTIME_DIR=./runtime
HOST_DATA_DIR=./private_runtime/data
HOST_BEST_FEATURES_DIR=./private_runtime/best_features
HOST_QUANTIZED_MODELS_DIR=./private_runtime/quantized_models
HOST_MODELS_PARAMETERS_DIR=./private_runtime/models_parameters
HOST_TRANSFORMER_OUTPUTS_DIR=./private_runtime/transformer_outputs
HOST_HISTORY_DIR=./private_runtime/history
HOST_RESULTS_DIR=./private_runtime/results
HOST_PRODUCTION_PREDICTIONS_DIR=./private_runtime/production_predictions

TRAIN_DATA_PATH=private_runtime/data/historical_daily.parquet
TRAIN_ALL_CODES_PATH=private_runtime/data/target_codes_models_columns_order.json
TRAIN_BEST_FEATURES_PREFIX=runtime/best_features/BEST_features_NOSMOOTH_
```

`HOST_*` values are host paths. `TRAIN_*` values are container paths read from
inside `/app`.

Check the Docker Compose configuration:

```powershell
Set-Location $TrainingRepo
docker compose config
```

## 5. Real-Data Preflight

Run a local preflight before starting training:

```powershell
Set-Location $TrainingRepo
python scripts\preflight_training.py `
  --data-path private_runtime\data\historical_daily.parquet `
  --codes-path private_runtime\data\target_codes_models_columns_order.json `
  --target-code DEMAND__TOTAL `
  --best-features-prefix private_runtime\best_features\BEST_features_NOSMOOTH_
```

Replace `DEMAND__TOTAL` with a real code from
`target_codes_models_columns_order.json`.

## 6. Start MLflow

Build and start PostgreSQL plus MLflow:

```powershell
Set-Location $TrainingRepo
docker compose build
docker compose up -d postgres mlflow
docker compose ps
```

Open MLflow using the port configured in `.env`:

```powershell
$MlflowPort = ((Select-String -Path .env -Pattern '^MLFLOW_HOST_PORT=').Line -split '=', 2)[1]
$MlflowUrl = "http://127.0.0.1:$MlflowPort"
Invoke-WebRequest "$MlflowUrl/health"
Start-Process $MlflowUrl
```

Follow logs when needed:

```powershell
docker compose logs -f mlflow
```

## 7. Train One Real Code

Set the target code and experiment setup:

```powershell
Set-Location $TrainingRepo
$env:TRAIN_TARGET_CODE="DEMAND__TOTAL"
$env:TRAIN_EXPERIMENT_SETUP="7_7"
```

Run one training and quantization job:

```powershell
docker compose --profile train run --rm train-one
```

Refresh MLflow in the browser opened in step 6.

Check generated private artifacts:

```powershell
Get-ChildItem private_runtime\quantized_models -Recurse
Get-ChildItem private_runtime\models_parameters -Recurse
Get-ChildItem private_runtime\transformer_outputs -Recurse
Get-ChildItem private_runtime\history -Recurse
```

## 8. Train a Small Batch, Then All Codes

First run only two codes:

```powershell
Set-Location $TrainingRepo
$env:TRAIN_ALL_LIMIT="2"
docker compose --profile all run --rm train-all
Remove-Item Env:\TRAIN_ALL_LIMIT
```

If that works, run all configured codes:

```powershell
docker compose --profile all run --rm train-all
```

## 9. Validate Real Model Bundle

```powershell
python "$InferenceRepo\production\validate_model_bundle.py" `
  --model-folder "$TrainingRepo\private_runtime\quantized_models" `
  --allow-real-data
```

Expected result:

- `contains_real_data` is accepted only because `--allow-real-data` is present;
- model layout is `code/model_type/weights`;
- each trained code has the required quantized weight files.

## 10. Run Real Inference

Build the inference image:

```powershell
Set-Location $InferenceRepo
docker build -t predap-inference .
```

Run inference with private mounts:

```powershell
$TrainingRuntime = Join-Path $TrainingRepo "private_runtime"

docker run --rm `
  -v "$TrainingRuntime\data:/app/data" `
  -v "$TrainingRuntime\quantized_models:/app/models" `
  -v "$TrainingRuntime\best_features:/app/best_features" `
  -v "$TrainingRuntime\results:/app/results" `
  -v "$TrainingRuntime\production_predictions:/app/output" `
  predap-inference `
  --input-directory /app/data/historical_daily.parquet `
  --old-input-directory /app/data/historical_daily.csv `
  --model-folder /app/models `
  --output-path /app/output/real/final_output_predictions `
  --metrics-df-path /app/output/production_evaluation_metrics.parquet `
  --diagnostic-covariates-path /app/best_features/BEST_features_NOSMOOTH_ `
  --model-selection-metrics-dir /app/results
```

Inspect outputs:

```powershell
Get-ChildItem "$TrainingRepo\private_runtime\production_predictions" -Recurse
```

## 11. Safety Check Before Publishing

The safety check is strict and intentionally rejects `runtime/`,
`private_runtime/`, `.env`, Parquet, Excel and model-weight files. Run it
against the exported repositories, not against an active development workspace
that contains generated toy or real outputs.

From the complete source workspace, export with safety enabled:

```powershell
Set-Location $SourceRoot
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\export_independent_repos.ps1 `
  -OutputRoot dist\github-repos `
  -Force `
  -RunSafetyCheck
```

This step requires Option A. If you are working from already exported GitHub
repositories, skip to step 15 after validation. Publishing new split repos from
GitHub clones is a normal `git add`, `git commit` and `git push` flow per repo;
the multi-repo export script needs the complete source workspace.

## 12. Export Independent GitHub Repositories

If you did not already export in the previous step, create clean publishable
copies now:

```powershell
Set-Location $SourceRoot
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\export_independent_repos.ps1 `
  -OutputRoot dist\github-repos `
  -Force `
  -RunSafetyCheck
```

The export creates:

```text
dist\github-repos\predap-platform
dist\github-repos\predap-data-retrieval
dist\github-repos\predap-cclr
dist\github-repos\predap-training
dist\github-repos\predap-inference
```

Preview Git initialization, commits and remotes:

```powershell
Set-Location $SourceRoot
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 `
  -ReposRoot dist\github-repos `
  -RemoteBaseUrl https://github.com/<org> `
  -DryRun
```

## 13. Create Empty GitHub Repositories

First choose the real GitHub owner. This must be your GitHub username or
organization, not the placeholder:

```powershell
$Org = "<your-github-user-or-org>"
```

Option A: create them in the GitHub web UI with these exact names:

```text
predap-platform
predap-data-retrieval
predap-cclr
predap-training
predap-inference
```

Do not add README, license or `.gitignore` in GitHub. The export already
contains those files.

Option B: create them with GitHub CLI.

Check whether `gh` is installed:

```powershell
Get-Command gh -ErrorAction SilentlyContinue
```

If the command prints nothing or raises `CommandNotFoundException`, install
GitHub CLI or use Option A. After installing it, open a new PowerShell window
so the updated `PATH` is loaded.

Authenticate:

```powershell
gh auth login
```

Create the repositories:

```powershell
$Visibility = "--private"
$Repos = @(
  "predap-platform",
  "predap-data-retrieval",
  "predap-cclr",
  "predap-training",
  "predap-inference"
)

foreach ($Repo in $Repos) {
  gh repo create "$Org/$Repo" $Visibility
}
```

Use `--public` instead of `--private` only when you are ready to publish
publicly.

If `gh` is not available, the manual GitHub web UI path is equivalent. The
publish script only needs the empty remote repositories to exist before
`-Push`.

## 14. Push to GitHub

After the empty GitHub repositories exist, push:

```powershell
Set-Location $SourceRoot
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 `
  -ReposRoot dist\github-repos `
  -RemoteBaseUrl https://github.com/<org> `
  -Push
```

If a remote already exists and points somewhere else, replace it explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 `
  -ReposRoot dist\github-repos `
  -RemoteBaseUrl https://github.com/<org> `
  -ForceRemote `
  -Push
```

If you already pushed an initial broken export to brand-new repositories and
need to replace that first public release, use the explicit safer force mode:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 `
  -ReposRoot dist\github-repos `
  -RemoteBaseUrl https://github.com/<org> `
  -ForcePush `
  -Push
```

`-ForcePush` uses `git push --force-with-lease`. Use it only when those remote
repositories are disposable initial exports or when you are sure nobody else's
work will be overwritten.

## 15. Stop Local Services

```powershell
Set-Location $TrainingRepo
docker compose down
```

Private artifacts remain under ignored `private_runtime/` and `runtime/`
folders. Do not move them into exported repositories.
