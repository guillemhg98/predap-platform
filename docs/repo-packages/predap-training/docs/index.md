# PREDAP Training

This repository owns Transformer training, quantization and MLflow tracking for
PREDAP.

Public GitHub content must stay limited to code, documentation and synthetic
examples. Real training data, model weights and MLflow artifacts remain in
private runtime storage.

## What This Repo Does

| Task | Entrypoint |
|---|---|
| Check public contracts with toy data | `examples/synthetic/predap_synthetic_workflow.py` |
| Validate real training inputs | `scripts/preflight_training.py` |
| Train and quantize one code/horizon | `docker compose --profile train run --rm train-one` |
| Train configured batches | `docker compose --profile all run --rm train-all` |
| Import copied old artifacts into MLflow | `docker compose --profile mlflow-import run --rm mlflow-import` |

## Public Smoke Test

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
```

This creates dummy data and dummy models only. It does not create MLflow runs.

## Private Runtime Folders

Create ignored local folders before real training:

```powershell
New-Item -ItemType Directory -Force `
  private_runtime\data, `
  private_runtime\best_features, `
  private_runtime\quantized_models, `
  private_runtime\models_parameters, `
  private_runtime\transformer_outputs, `
  private_runtime\history, `
  private_runtime\production_predictions, `
  runtime\mlflow
```

Real inputs go here:

```text
private_runtime/data/historical_daily.parquet
private_runtime/data/historical_daily.csv
private_runtime/data/target_codes_models_columns_order.json
private_runtime/best_features/BEST_features_NOSMOOTH_<CODE>.xlsx
```

## Start MLflow

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
docker compose build
docker compose up -d postgres mlflow
docker compose ps
```

Default host ports are `55001` for MLflow and `55433` for PostgreSQL. If `.env`
already exists, update `MLFLOW_HOST_PORT` and `POSTGRES_HOST_PORT` there because
ignored local files are not replaced by `git pull`.

Open the UI:

```powershell
$MlflowPort = ((Select-String -Path .env -Pattern '^MLFLOW_HOST_PORT=').Line -split '=', 2)[1]
$MlflowUrl = "http://127.0.0.1:$MlflowPort"
Start-Process $MlflowUrl
```

## Standalone Contract

The standalone clone includes all code needed by training and quantization,
including the quantization helper and the CCLR import bridge. It does not bundle
real data, trained models, MLflow runs or CCLR outputs.

Packaging fixes do not change model defaults. Epochs, horizons, learning rate,
architecture choices and batch-size logic are controlled by `conf/` and command
overrides.

For Windows local runs, `scripts/train_all_codes.py` launches child Python
processes with UTF-8 settings and training messages avoid non-ASCII symbols.

## Train One Horizon

```powershell
$env:TRAIN_TARGET_CODE="<CODE>"
$env:TRAIN_EXPERIMENT_SETUP="7_7"
docker compose --profile train run --rm train-one
```

## Train Long Horizons

```powershell
$env:TRAIN_TARGET_CODE="DEMAND__TOTAL"

$env:TRAIN_EXPERIMENT_SETUP="182_182"
docker compose --profile train run --rm train-one

$env:TRAIN_EXPERIMENT_SETUP="365_182"
docker compose --profile train run --rm train-one
```

## Import Recovered Artifacts into MLflow

```powershell
$env:IMPORT_MODEL_CODE="DEMAND__TOTAL"
$env:IMPORT_SOURCE_LABEL="recovered_from_predap_production_simplified"
docker compose --profile mlflow-import run --rm mlflow-import
```

See [Training Workflow](training-workflow.md).
