# Private Runtime Setup From GitHub

This page explains what to do after cloning the public GitHub repositories.
GitHub contains code, docs and synthetic fixtures only. Real data, real CCLR
outputs, trained models, MLflow artifacts and predictions must be downloaded or
generated privately and placed under ignored runtime folders.

Use this page before running the real tutorials.

## Python and Docker Requirement

The public toy workflow and documentation build can run without TensorFlow. Real
training, quantization and production-style inference need Docker or a local
Python 3.10-3.12 environment. Avoid Python 3.13 for these installs while
`requirements-training-local.txt` installs `tensorflow-cpu<2.18,>=2.16`; pip
will not find a compatible TensorFlow wheel.

On Windows, if `py -3.12` is not available, use the installed Python path
directly:

```powershell
C:\Users\Guillem\AppData\Local\Programs\Python\Python310\python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-training-local.txt
```

## 1. Clone the Public Code

Clone the platform repository or the split repositories:

```powershell
git clone https://github.com/guillemhg98/predap-platform.git
Set-Location predap-platform
```

The public clone will not contain:

- real `data/` or `private_runtime/` folders;
- real `.parquet`, `.csv` or `.xlsx` files;
- trained `.h5` or `.keras` models;
- MLflow run folders;
- production predictions.

That absence is intentional.

## 2. Create the Private Folder Tree

Create the ignored private runtime folders from the platform root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\create_private_runtime_skeleton.ps1 -Profile platform
```

Expected private layout:

```text
private_runtime/
  data/
    historical_daily.parquet
    inference_daily.parquet
    historical_daily.csv
    target_codes_models_columns_order.json
    models_columns_orders.txt
  best_features/
    BEST_features_NOSMOOTH_<CODE>.xlsx
  quantized_models/
    manifest.json
    <CODE>/
      univariate_model/
      diagnostics_model/
      seasonal_model/
  models_parameters/
    <CODE>/
  transformer_outputs/
    models_covid_token/
  history/
  results/
    performance_*.json
    recovered_models/
      performance_*.json
  production_predictions/
    real/
    smoke/
runtime/
  mlflow/
```

## 3. Download or Generate Private Artifacts

The public repo does not know where your private storage lives. Download or copy
the following artifact groups from your secure location.

| Artifact group | Private source | Destination |
|---|---|---|
| Retrieval finals | `AQUAS_DATA_RETRIEVAL-git/data/data/finals/` or secure object storage | `private_runtime/data/` |
| CCLR best features | CCLR private run output | `private_runtime/best_features/` |
| Quantized weights | Training private run output | `private_runtime/quantized_models/` |
| Model parameters | Training private run output | `private_runtime/models_parameters/` |
| Full Keras models | Training private run output | `private_runtime/transformer_outputs/` |
| Training histories | Training private run output | `private_runtime/history/` |
| Evaluation WAPE JSON | Training or recovered artifact output | `private_runtime/results/` |
| MLflow state | Local/private MLflow volume, optional | `runtime/mlflow/` |

For the current local recovered folder, the source root is:

```powershell
$ExternalRoot = "D:\TRANSFORMERS_PREDAP-predap_production_simplified\TRANSFORMERS_PREDAP-predap_production_simplified"
$RetrievalFinals = Join-Path $ExternalRoot "AQUAS_DATA_RETRIEVAL-git\data\data\finals"
$ExternalRuntime = Join-Path $ExternalRoot "runtime"
```

On another machine, replace these paths with your real private download path.

## 4. Retrieval Data Files

The retrieval module must provide daily time-series data and code metadata.

Recommended source folder:

```text
finals/
  demand_diagnosis_joined.parquet
  demand_diagnosis_joined.csv
  demand_diagnosis_joined_training_until_YYYY-MM-DD_no_imputed.parquet
  target_codes_models_columns_order.json
  models_columns_orders.txt
```

Copy them into the platform runtime names:

```powershell
Copy-Item "$RetrievalFinals\demand_diagnosis_joined_training_until_2026-06-30_no_imputed.parquet" `
  private_runtime\data\historical_daily.parquet `
  -Force

Copy-Item "$RetrievalFinals\demand_diagnosis_joined.parquet" `
  private_runtime\data\inference_daily.parquet `
  -Force

Copy-Item "$RetrievalFinals\demand_diagnosis_joined.csv" `
  private_runtime\data\historical_daily.csv `
  -Force

Copy-Item "$RetrievalFinals\target_codes_models_columns_order.json" `
  private_runtime\data\target_codes_models_columns_order.json `
  -Force

Copy-Item "$RetrievalFinals\models_columns_orders.txt" `
  private_runtime\data\models_columns_orders.txt `
  -Force
```

### Time-Series Schema

`historical_daily.parquet`, `inference_daily.parquet` and
`historical_daily.csv` must have:

| Column | Required | Type | Notes |
|---|---:|---|---|
| `timestamp` | yes | date or datetime | One row per day. The default inference origin is the latest timestamp in `inference_daily.parquet`. |
| `<CODE>` columns | yes | numeric | Every code listed in `target_codes_models_columns_order.json` must exist as a column. |
| extra covariate columns | optional | numeric/date-compatible | Allowed only if downstream code expects them. |

Example:

```text
timestamp,DEMAND__TOTAL,DEMAND__SERVEI_CODI__URG,DEMAND__TIPUS_CLASS__CALTRE__RS__RS_63
2024-01-01,123,45,6
2024-01-02,118,42,4
```

Rules:

- keep code column names exactly stable across training and inference;
- do not rename `DEMAND__TOTAL` to `DEMAND_TOTAL` or `TOTAL`;
- use daily granularity;
- avoid duplicate timestamps;
- numeric target columns should not be stored as free text;
- keep real data out of Git, including aggregated data.

### Aggregation and Metadata Files

`target_codes_models_columns_order.json` is the canonical aggregation/target
metadata file for training and inference:

```json
[
  "DEMAND__TOTAL",
  "DEMAND__SERVEI_CODI__URG",
  "DEMAND__TIPUS_CLASS__CALTRE__RS__RS_63"
]
```

`models_columns_orders.txt` is the legacy/plain-text view of the same modeled
columns:

```text
DEMAND__TOTAL
DEMAND__SERVEI_CODI__URG
DEMAND__TIPUS_CLASS__CALTRE__RS__RS_63
```

Both files should describe the same target columns. The JSON is the one used by
the current training scripts.

## 5. CCLR Best-Feature Files

CCLR must provide one Excel file per modeled code:

```text
private_runtime/best_features/BEST_features_NOSMOOTH_<CODE>.xlsx
```

For example:

```text
private_runtime/best_features/BEST_features_NOSMOOTH_DEMAND__TOTAL.xlsx
```

Each file must contain:

| Column | Required | Meaning |
|---|---:|---|
| `LAG` | yes | Forecast horizon, for example `7`, `14`, `30`, `60`, `182`, `365`. |
| `predictors` | yes | Comma-separated covariate column names selected for that horizon. |

The inference and training code resolve files by prefix:

```text
runtime/best_features/BEST_features_NOSMOOTH_
```

Inside Docker this prefix points to `/app/runtime/best_features/`.

## 6. Model and Evaluation Artifacts

A real model bundle must include quantized weights and a manifest:

```text
private_runtime/quantized_models/
  manifest.json
  <CODE>/
    univariate_model/
      <CODE>_univariate_model_7fh_7lb_f16_weights.h5
    diagnostics_model/
      <CODE>_diagnostics_model_7fh_7lb_f16_weights.h5
    seasonal_model/
      <CODE>_seasonal_model_7fh_7lb_f16_weights.h5
```

For default horizons the expected pairs are:

| Forecast | Lookback | Experiment setup |
|---:|---:|---|
| 7 | 7 | `7_7` |
| 14 | 14 | `14_14` |
| 30 | 60 | `60_30` |
| 60 | 60 | `60_60` |
| 182 | 182 | `182_182` |
| 365 | 182 | `365_182` |

Additional supporting artifacts should be copied when available:

```text
private_runtime/models_parameters/<CODE>/*.json
private_runtime/transformer_outputs/models_covid_token/*.keras
private_runtime/history/*.pkl
private_runtime/results/**/*.json
```

The `private_runtime/results` folder is important for stage-aware inference.
It contains `performance_*.json` files with WAPE for `univariate`,
`diagnostics` and `seasonal`. Inference reads these metrics and stops at the
best stage for each code and horizon.

## 7. Configure `.env`

Create `.env` locally:

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

Minimum private path values:

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

# Bundled in standalone predap-training. Change only for a custom CCLR checkout.
HOST_CCLR_REPO_DIR=./predap-cclr
CCLR_REPO_PATH=/app/predap-cclr

INFERENCE_OUTPUT_PREFIX=real/final_output_predictions
INFERENCE_MODEL_SELECTION_METRICS_DIR=private_runtime/results
```

`HOST_*` values are host paths. `TRAIN_*` values are paths inside the training
container working directory `/app`.

Default `.env.example` ports are:

```text
MLFLOW_HOST_PORT=55001
POSTGRES_HOST_PORT=55433
```

If you already have a local `.env`, `git pull` will not modify it. Update those
values manually if Docker reports that `5433` or another old port is already
allocated.

## 8. Validate Before Running

Run the private contract checker:

```powershell
python scripts\check_private_runtime_contract.py --runtime-root private_runtime
```

For a full real run where you expect features, models and WAPE metrics already
to exist:

```powershell
python scripts\check_private_runtime_contract.py `
  --runtime-root private_runtime `
  --require-best-features `
  --require-models `
  --require-selection-metrics
```

Do not use `--require-best-features` when you intentionally want the training
entrypoint to generate missing CCLR Excel files. In that case, validate the base
runtime without the flag, then run `scripts\preflight_training.py` for the
specific target code. In standalone `predap-training`, CCLR generation uses the
bundled `predap-cclr/` folder. For local Python runs:

```powershell
$env:CCLR_REPO_PATH="D:\PREDAP_GITHUB_CLEAN_CHECK\predap-training\predap-cclr"
```

The standalone training repo includes its own quantization helper and CCLR import
bridge. These packaging fixes do not alter epochs, learning rate, architecture,
horizons or batch-size logic; those remain defined by `conf/` and explicit
overrides.

If you run training through Docker from a standalone `predap-training` clone,
also set this in `.env`:

```text
HOST_CCLR_REPO_DIR=./predap-cclr
CCLR_REPO_PATH=/app/predap-cclr
```

Validate the quantized model bundle:

```powershell
python PREDAP_INFERENCE\production\validate_model_bundle.py `
  --model-folder private_runtime\quantized_models `
  --allow-real-data
```

Training preflight for one code:

```powershell
python scripts\preflight_training.py `
  --data-path private_runtime\data\historical_daily.parquet `
  --codes-path private_runtime\data\target_codes_models_columns_order.json `
  --target-code DEMAND__TOTAL `
  --best-features-prefix private_runtime\best_features\BEST_features_NOSMOOTH_
```

## 9. Run Real Inference After Setup

Build the inference image:

```powershell
docker build -t predap-inference .\PREDAP_INFERENCE
```

Run a stage-aware prediction for selected codes:

```powershell
$Repo = (Get-Location).Path

docker run --rm `
  -v "$Repo\private_runtime\data:/app/data" `
  -v "$Repo\private_runtime\quantized_models:/app/models" `
  -v "$Repo\private_runtime\best_features:/app/best_features" `
  -v "$Repo\private_runtime\results:/app/results" `
  -v "$Repo\private_runtime\production_predictions:/app/output" `
  predap-inference `
  --input-directory /app/data/inference_daily.parquet `
  --old-input-directory /app/data/historical_daily.csv `
  --model-folder /app/models `
  --output-path /app/output/real/final_output_predictions `
  --metrics-df-path /app/output/production_evaluation_metrics.parquet `
  --diagnostic-covariates-path /app/best_features/BEST_features_NOSMOOTH_ `
  --model-selection-metrics-dir /app/results `
  --code DEMAND__TOTAL `
  --lookback-list 7,14,60,60 `
  --forecast-list 7,14,30,60
```

Inspect:

```powershell
Get-Content private_runtime\production_predictions\real\final_output_predictions_wide.csv -TotalCount 10
```

Look for:

```text
<CODE>__model_stage_reached
<CODE>__selected_stage_wape
<CODE>__univariate_wape
<CODE>__diagnostics_wape
<CODE>__seasonal_wape
```

## 10. Run Daily Inference and Log Each Day to MLflow

Operationally, inference is intended to run every day. Each prediction origin
date gets its own output folder and its own MLflow run.

Start MLflow:

```powershell
docker compose up -d postgres mlflow
```

Run the latest available week in `private_runtime\data\inference_daily.parquet`.
If `DAILY_INFERENCE_END_DATE` is empty, the script uses the latest timestamp in
that file and walks back `DAILY_INFERENCE_DAYS` calendar days:

```powershell
$env:DAILY_INFERENCE_DAYS="7"
$env:DAILY_INFERENCE_CODES="DEMAND__TOTAL,DEMAND__TIPUS_CLASS__DALTRE__RS__RS_71,DEMAND__TIPUS_CLASS__CALTRE__RS__RS_63"
$env:DAILY_INFERENCE_LOOKBACK_LIST="7,14,60,60"
$env:DAILY_INFERENCE_FORECAST_LIST="7,14,30,60"
$env:DAILY_INFERENCE_BATCH_LABEL="week_test_latest"

docker compose --profile daily-inference run --rm daily-inference

Remove-Item Env:\DAILY_INFERENCE_DAYS -ErrorAction SilentlyContinue
Remove-Item Env:\DAILY_INFERENCE_CODES -ErrorAction SilentlyContinue
Remove-Item Env:\DAILY_INFERENCE_LOOKBACK_LIST -ErrorAction SilentlyContinue
Remove-Item Env:\DAILY_INFERENCE_FORECAST_LIST -ErrorAction SilentlyContinue
Remove-Item Env:\DAILY_INFERENCE_BATCH_LABEL -ErrorAction SilentlyContinue
```

For a full real run with all target codes, prefer the retrieval JSON instead of
listing codes by hand. This also avoids technical imputation columns:

```powershell
$env:DAILY_INFERENCE_DAYS="7"
$env:DAILY_INFERENCE_CODES_FILE="/app/private_runtime/data/target_codes_models_columns_order.json"
$env:DAILY_INFERENCE_WORKERS="4"
$env:DAILY_INFERENCE_TF_INTRA_OP_THREADS="1"
$env:DAILY_INFERENCE_TF_INTER_OP_THREADS="1"
$env:DAILY_INFERENCE_BATCH_LABEL="week_all_codes_parallel"

docker compose --profile daily-inference run --rm daily-inference

Remove-Item Env:\DAILY_INFERENCE_DAYS -ErrorAction SilentlyContinue
Remove-Item Env:\DAILY_INFERENCE_CODES_FILE -ErrorAction SilentlyContinue
Remove-Item Env:\DAILY_INFERENCE_WORKERS -ErrorAction SilentlyContinue
Remove-Item Env:\DAILY_INFERENCE_TF_INTRA_OP_THREADS -ErrorAction SilentlyContinue
Remove-Item Env:\DAILY_INFERENCE_TF_INTER_OP_THREADS -ErrorAction SilentlyContinue
Remove-Item Env:\DAILY_INFERENCE_BATCH_LABEL -ErrorAction SilentlyContinue
```

The parallel runner creates `_shards/` below each daily output folder, merges
all shards into the standard files and deletes the temporary shards by default.
Set `DAILY_INFERENCE_KEEP_SHARDS=1` only when debugging a failed shard.

To reproduce an exact week, set both dates:

```powershell
$env:DAILY_INFERENCE_START_DATE="YYYY-MM-DD"
$env:DAILY_INFERENCE_END_DATE="YYYY-MM-DD"
docker compose --profile daily-inference run --rm daily-inference
Remove-Item Env:\DAILY_INFERENCE_START_DATE -ErrorAction SilentlyContinue
Remove-Item Env:\DAILY_INFERENCE_END_DATE -ErrorAction SilentlyContinue
```

Outputs are written by origin date:

```text
private_runtime/production_predictions/real/daily/YYYY-MM-DD/final_output_predictions_wide.csv
private_runtime/production_predictions/real/daily/YYYY-MM-DD/final_output_predictions_wide.parquet
private_runtime/production_predictions/real/daily/YYYY-MM-DD/final_output_predictions_selected_long.parquet
private_runtime/production_predictions/real/daily/daily_inference_summary.csv
```

Open MLflow and inspect the `PREDAP_Inference_Outputs` experiment. Each run is
named `daily_inference_YYYY-MM-DD` and stores `prediction_origin_date`,
`batch_label`, row counts and the daily output files as artifacts.

## 11. Common Setup Problems

| Symptom | Likely cause | Fix |
|---|---|---|
| `Missing private runtime directories` | Folder tree was not created. | Run the `New-Item` command in section 2. |
| `Codes JSON not found` | Retrieval metadata was not copied. | Copy `target_codes_models_columns_order.json` into `private_runtime/data/`. |
| `code columns from JSON are missing` | Dataset and JSON do not match. | Regenerate retrieval finals or use the matching JSON for that dataset. |
| `Missing best-feature files` | CCLR outputs are absent. | Run CCLR privately or copy `BEST_features_NOSMOOTH_<CODE>.xlsx`. |
| `Missing quantized model manifest` | Models were not trained/recovered. | Run training or copy `private_runtime/quantized_models/manifest.json`. |
| Stage is always `seasonal` with fallback reason | WAPE performance JSON files are missing. | Copy `performance_*.json` to `private_runtime/results/`. |
| Wide prediction columns have wrong code names | Historical columns were renamed downstream. | Keep names identical to `target_codes_models_columns_order.json`. |

## 12. Before Publishing

Never commit `private_runtime/`, `runtime/`, `.env`, real data or model files.
Before pushing exported repositories:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_github_safety.ps1 -Path dist\github-repos
```
