# Full Platform Workflow

This tutorial explains how to publish and run the PREDAP platform with all
submodules.

For the clearest first run, follow
[Practical Runbook](practical-runbook.md). This page focuses on the platform
split, submodules and the broader workflow.

It has two tracks:

- **toy track**: fully public, uses synthetic data and dummy models;
- **real-data track**: private, uses institutional data and real trained models
  stored outside GitHub.

For a stage-by-stage mapping between toy artifacts and real private
subprocesses, see [Toy vs Real Integration Map](../platform/toy-vs-real-map.md).

## 1. Repository Layout

The platform is split into five repositories:

| Repository | Role |
|---|---|
| `predap-platform` | Documentation, orchestration and submodule parent repo. |
| `predap-data-retrieval` | Data connectors and historical dataset export. |
| `predap-cclr` | Feature selection and diagnostic covariate generation. |
| `predap-training` | Transformer training, MLflow and quantization. |
| `predap-inference` | Model bundle validation and prediction generation. |

The platform repo should include the other four repos as Git submodules under:

```text
modules/
  predap-data-retrieval/
  predap-cclr/
  predap-training/
  predap-inference/
```

## 2. Prepare Clean GitHub Repositories

From the current workspace:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\export_independent_repos.ps1 -OutputRoot dist\github-repos -Force -RunSafetyCheck
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 -ReposRoot dist\github-repos -RemoteBaseUrl https://github.com/<org> -DryRun
```

Only publish the exported folders if the safety check passes and the dry run
shows the expected remotes.

Create one GitHub repository for each exported folder, then push:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 -ReposRoot dist\github-repos -RemoteBaseUrl https://github.com/<org> -Push
```

This initializes, commits, configures `origin`, sets `main`, and pushes:

```text
predap-platform
predap-data-retrieval
predap-cclr
predap-training
predap-inference
```

## 3. Add Submodules to the Platform Repo

After the four module repositories exist:

```powershell
cd dist\github-repos\predap-platform
mkdir modules
git submodule add https://github.com/<org>/predap-data-retrieval.git modules/predap-data-retrieval
git submodule add https://github.com/<org>/predap-cclr.git modules/predap-cclr
git submodule add https://github.com/<org>/predap-training.git modules/predap-training
git submodule add https://github.com/<org>/predap-inference.git modules/predap-inference
git add .gitmodules modules
git commit -m "Add PREDAP module submodules"
git push
```

Users clone the full platform with:

```bash
git clone --recurse-submodules https://github.com/<org>/predap-platform.git
```

If they cloned without submodules:

```bash
git submodule update --init --recursive
```

## 4. Enable GitHub Pages

For `predap-platform`:

1. Open **Settings > Pages**.
2. Set **Source** to **GitHub Actions**.
3. Push to `main`.
4. Confirm that the `Docs` workflow succeeds.

The platform Pages site is the canonical documentation for the whole system.

The independent repos can also enable Pages if they contain `mkdocs.yml` and a
docs workflow. At minimum, `predap-cclr`, `predap-data-retrieval` and
`predap-inference` are prepared for this.

## 5. Toy Track: Run Everything With Synthetic Data

From the platform root:

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
```

This simulates the full platform:

| Real module | Toy output |
|---|---|
| Data retrieval | `runtime/synthetic_demo/retrieval_export/historical_daily.csv` |
| CCLR/training input metadata | `target_codes_models_columns_order.json` |
| Training | `runtime/synthetic_demo/model_bundle/` |
| Inference | `runtime/synthetic_demo/inference/predictions.csv` |

Validate the dummy model bundle:

```powershell
python PREDAP_INFERENCE/production/validate_model_bundle.py --model-folder runtime/synthetic_demo/model_bundle
```

Check the generated prediction table:

```powershell
Get-Content runtime\synthetic_demo\inference\predictions.csv -TotalCount 10
```

This toy flow is what CI runs on GitHub.

## 6. Real-Data Track: Private End-to-End Run

Keep all real data outside GitHub. Recommended local layout:

```text
private_runtime/
  data/
    historical_daily.parquet
    historical_daily.csv
    target_codes_models_columns_order.json
  best_features/
    BEST_features_NOSMOOTH_<CODE>.xlsx
  quantized_models/
  models_parameters/
  transformer_outputs/
  production_predictions/
```

Copy `.env.example` to `.env` and point host paths to private folders:

```powershell
Copy-Item .env.example .env
```

Example values:

```text
HOST_RUNTIME_DIR=./private_runtime
HOST_DATA_DIR=./private_runtime/data
HOST_BEST_FEATURES_DIR=./private_runtime/best_features
HOST_QUANTIZED_MODELS_DIR=./private_runtime/quantized_models
HOST_MODELS_PARAMETERS_DIR=./private_runtime/models_parameters
HOST_TRANSFORMER_OUTPUTS_DIR=./private_runtime/transformer_outputs
HOST_PRODUCTION_PREDICTIONS_DIR=./private_runtime/production_predictions
TRAIN_DATA_PATH=private_runtime/data/historical_daily.parquet
TRAIN_ALL_CODES_PATH=private_runtime/data/target_codes_models_columns_order.json
TRAIN_BEST_FEATURES_PREFIX=runtime/best_features/BEST_features_NOSMOOTH_
```

Start tracking services:

```powershell
docker compose build
docker compose up -d postgres mlflow
```

Run private training:

```powershell
$env:TRAIN_TARGET_CODE="<CODE>"
$env:TRAIN_EXPERIMENT_SETUP="7_7"
docker compose --profile train run --rm train-one
```

The training preflight checks the same `TRAIN_DATA_PATH`,
`TRAIN_ALL_CODES_PATH` and `TRAIN_BEST_FEATURES_PREFIX` values that the Hydra
training entrypoint receives.

Run a private batch:

```powershell
docker compose --profile all run --rm train-all
```

Validate the private model bundle before inference:

```powershell
python PREDAP_INFERENCE/production/validate_model_bundle.py --model-folder private_runtime/quantized_models --allow-real-data
```

Run inference with private mounted paths:

```bash
docker run --rm \
  -v "$PWD/private_runtime/data:/app/data" \
  -v "$PWD/private_runtime/quantized_models:/app/models" \
  -v "$PWD/private_runtime/best_features:/app/best_features" \
  -v "$PWD/private_runtime/results:/app/results" \
  -v "$PWD/private_runtime/production_predictions:/app/output" \
  predap-inference \
  --input-directory /app/data/historical_daily.parquet \
  --old-input-directory /app/data/historical_daily.csv \
  --model-folder /app/models \
  --output-path /app/output/real/final_output_predictions \
  --metrics-df-path /app/output/production_evaluation_metrics.parquet \
  --diagnostic-covariates-path /app/best_features/BEST_features_NOSMOOTH_ \
  --model-selection-metrics-dir /app/results
```

## 7. Before Every Push

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_github_safety.ps1 -Path dist\github-repos
```

Also check Git status manually in each repo:

```bash
git status --short
```

No real data, model weights, MLflow runs, runtime outputs or `.env` files should
appear.
