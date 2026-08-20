# Practical Runbook: Toy Data, Real Data, MLflow and Prediction

This is the main copy-paste guide for operating PREDAP from GitHub or from the
complete local source bundle. Follow it in order the first time.

If you start from a clean GitHub clone, read
[Private Runtime Setup](../platform/private-runtime-setup.md) before the real
data sections. It defines the private folders to create, which artifacts to
download and the required schemas for time series, aggregation metadata, CCLR
files and model artifacts.

The idea is simple:

1. Use toy data to understand the file contracts without private data.
2. Copy real retrieval outputs into ignored private runtime folders.
3. Start MLflow.
4. Import recovered models or train new models.
5. Validate the model bundle.
6. Run prediction.
7. Publish only clean GitHub exports.

## 0. Choose Your Workspace Mode

Use one of these modes.

### Complete Source Bundle

Use this mode when one folder contains `docker-compose.yml`, `src/`,
`PREDAP_INFERENCE/`, `CCLR_PREDAP/` and `AQUAS_DATA_RETRIEVAL-git/`.

```powershell
cd C:\Users\Guillem\Desktop\TRANSFORMERS_PREDAP_lite_autocontingut
$SourceRoot = (Get-Location).Path
$PlatformRepo = $SourceRoot
$TrainingRepo = $SourceRoot
$InferenceRepo = Join-Path $SourceRoot "PREDAP_INFERENCE"
```

### Independent GitHub Repositories

Use this mode after the five repositories have been pushed to GitHub and cloned
as siblings.

```powershell
mkdir predap-workspace
cd predap-workspace

git clone https://github.com/guillemhg98/predap-platform.git
git clone https://github.com/guillemhg98/predap-data-retrieval.git
git clone https://github.com/guillemhg98/predap-cclr.git
git clone https://github.com/guillemhg98/predap-training.git
git clone https://github.com/guillemhg98/predap-inference.git

$Workspace = (Get-Location).Path
$PlatformRepo = Join-Path $Workspace "predap-platform"
$TrainingRepo = Join-Path $Workspace "predap-training"
$InferenceRepo = Join-Path $Workspace "predap-inference"
```

## 1. What Each Stage Means

| Stage | Toy data does this | Real data does this | How you know it worked |
|---|---|---|---|
| Retrieval | Writes a tiny synthetic daily table. | Your private retrieval process writes Parquet, CSV and code metadata. | The dataset has `timestamp` plus target-code columns. |
| CCLR | Skipped except for simple metadata. | Produces `BEST_features_NOSMOOTH_<CODE>.xlsx` files. | Training can find or create the feature file. |
| Training | Writes dummy JSON models. | Trains TensorFlow models, logs MLflow runs and exports quantized weights. | MLflow has runs and `private_runtime/quantized_models` has `.h5` files. |
| MLflow | Not used. | Tracks real training runs and imported recovered artifacts. | The MLflow UI shows experiments and artifacts. |
| Inference | Writes synthetic prediction rows. | Loads real quantized weights and writes production predictions. | The output folder contains prediction and metrics files. |
| Publishing | Exports code, docs and synthetic fixtures. | Real data and real weights stay private. | The safety check passes before push. |

## 2. Toy Data: Learn the Contracts

Run the public workflow:

```powershell
Set-Location $PlatformRepo
python examples\synthetic\predap_synthetic_workflow.py --output-dir runtime\synthetic_demo
```

Inspect each generated piece:

```powershell
Get-ChildItem runtime\synthetic_demo -Recurse
Get-Content runtime\synthetic_demo\retrieval_export\historical_daily.csv -TotalCount 5
Get-Content runtime\synthetic_demo\retrieval_export\target_codes_models_columns_order.json
Get-Content runtime\synthetic_demo\model_bundle\manifest.json
Get-Content runtime\synthetic_demo\inference\predictions.csv -TotalCount 10
Get-Content runtime\synthetic_demo\inference\predictions_wide.csv -TotalCount 10
Get-Content runtime\synthetic_demo\metrics.json
```

Validate the dummy model bundle:

```powershell
python "$InferenceRepo\production\validate_model_bundle.py" `
  --model-folder "$PlatformRepo\runtime\synthetic_demo\model_bundle"
```

Check the platform output contract:

```powershell
python "$PlatformRepo\scripts\validate_synthetic_outputs.py" `
  --output-dir "$PlatformRepo\runtime\synthetic_demo"
```

Expected result:

- `manifest.json` says `contains_real_data: false`;
- the JSON code list matches columns in `historical_daily.csv`;
- dummy model files exist;
- `predictions.csv` has the raw long prediction columns.
- `predictions_wide.csv` has one row per future date and one prediction column
  per target code.

Toy data is intentionally small. It explains the handoff between modules, not
model quality and not MLflow.

## 3. Real Data: Copy Retrieval Outputs

Start from the private retrieval `finals` folder:

```powershell
$RetrievalFinals = "D:\TRANSFORMERS_PREDAP-predap_production_simplified\TRANSFORMERS_PREDAP-predap_production_simplified\AQUAS_DATA_RETRIEVAL-git\data\data\finals"
```

Create ignored runtime folders:

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

Copy the files used by training and prediction:

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
```

Check the files:

```powershell
Get-ChildItem private_runtime\data
Get-Content private_runtime\data\target_codes_models_columns_order.json -TotalCount 20
```

## 4. Real Data: Configure `.env`

Create `.env`:

```powershell
Set-Location $TrainingRepo
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

Make sure these values are present:

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
TRAIN_TARGET_CODE=DEMAND__TOTAL
TRAIN_EXPERIMENT_SETUP=7_7
TRAIN_ALL_EXPERIMENT_SETUPS=7_7,14_14,60_30,60_60,182_182,365_182

INFERENCE_EXPERIMENT_NAME=PREDAP_Inference_Outputs
INFERENCE_OUTPUT_PREFIX=real/final_output_predictions
INFERENCE_PREDICTION_ORIGIN_DATE=
INFERENCE_METRICS_PATH=
INFERENCE_MODEL_SELECTION_METRICS_DIR=private_runtime/results
```

If ports `5433` or `5001` are already used, keep the old containers running and
change local ports:

```text
POSTGRES_HOST_PORT=5434
MLFLOW_HOST_PORT=5002
```

Check the effective Compose configuration:

```powershell
docker compose config
```

## 5. Real Data: Preflight

Check that the Parquet schema and target-code JSON agree:

```powershell
python -c "import json, pyarrow.parquet as pq; from pathlib import Path; p=Path('private_runtime/data/historical_daily.parquet'); c=Path('private_runtime/data/target_codes_models_columns_order.json'); s=pq.read_schema(p); codes=json.loads(c.read_text(encoding='utf-8-sig')); print('columns', len(s.names)); print('codes', len(codes)); print('first_codes', codes[:10]); print('missing', [x for x in codes if x not in s.names][:10])"
```

Expected:

- `missing` is `[]`;
- `DEMAND__TOTAL` appears in the code list;
- `timestamp` exists in the Parquet schema.

Run the training preflight for one code:

```powershell
python scripts\preflight_training.py `
  --data-path private_runtime\data\historical_daily.parquet `
  --codes-path private_runtime\data\target_codes_models_columns_order.json `
  --target-code DEMAND__TOTAL `
  --best-features-prefix private_runtime\best_features\BEST_features_NOSMOOTH_
```

## 6. Start MLflow

```powershell
Set-Location $TrainingRepo
docker compose build
docker compose up -d postgres mlflow
docker compose ps
```

Open MLflow using the port from `.env`:

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

## 7. Import Recovered Models into MLflow

Copied model files can be used by inference immediately, but MLflow only shows
them after they are logged as runs.

Dry-run the import first:

```powershell
python scripts\import_recovered_models_to_mlflow.py `
  --dry-run `
  --code DEMAND__TOTAL `
  --quantized-root private_runtime\quantized_models `
  --parameters-root private_runtime\models_parameters `
  --best-features-root private_runtime\best_features `
  --transformer-outputs-root private_runtime\transformer_outputs `
  --history-root private_runtime\history
```

Expected for the recovered local `DEMAND__TOTAL` bundle:

```text
Would import 7fh/7lb
Would import 14fh/14lb
Would import 30fh/60lb
Would import 60fh/60lb
```

Log them to MLflow:

```powershell
$env:IMPORT_MODEL_CODE="DEMAND__TOTAL"
$env:IMPORT_SOURCE_LABEL="recovered_from_predap_production_simplified"

docker compose --profile mlflow-import run --rm mlflow-import

Remove-Item Env:\IMPORT_MODEL_CODE -ErrorAction SilentlyContinue
Remove-Item Env:\IMPORT_SOURCE_LABEL -ErrorAction SilentlyContinue
```

In the MLflow UI, open the `PREDAP_Recovered_Artifacts` experiment. Each run is
one forecast/lookback pair and contains grouped artifacts.

## 8. Train One Real Code

This trains one target code and one configured horizon:

```powershell
Set-Location $TrainingRepo
$env:TRAIN_TARGET_CODE="DEMAND__TOTAL"
$env:TRAIN_EXPERIMENT_SETUP="7_7"

docker compose --profile train run --rm train-one

Remove-Item Env:\TRAIN_TARGET_CODE -ErrorAction SilentlyContinue
Remove-Item Env:\TRAIN_EXPERIMENT_SETUP -ErrorAction SilentlyContinue
```

Refresh MLflow. The training run should contain params, metrics, TensorFlow
artifacts and quantized output artifacts.

## 9. Train the Missing 182 and 365 Horizons

Run the long horizons from the same codebase and real dataset:

```powershell
Set-Location $TrainingRepo
$env:TRAIN_TARGET_CODE="DEMAND__TOTAL"

$env:TRAIN_EXPERIMENT_SETUP="182_182"
docker compose --profile train run --rm train-one

$env:TRAIN_EXPERIMENT_SETUP="365_182"
docker compose --profile train run --rm train-one

Remove-Item Env:\TRAIN_TARGET_CODE -ErrorAction SilentlyContinue
Remove-Item Env:\TRAIN_EXPERIMENT_SETUP -ErrorAction SilentlyContinue
```

`182_182` means forecast 182 days with lookback 182 days.
`365_182` means forecast 365 days with lookback 182 days.

To see active training containers:

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Command}}"
```

To stop a specific one:

```powershell
docker stop <container-name>
```

## 10. Validate the Real Model Bundle

```powershell
python "$InferenceRepo\production\validate_model_bundle.py" `
  --model-folder "$TrainingRepo\private_runtime\quantized_models" `
  --allow-real-data
```

Expected:

- the manifest is accepted with `--allow-real-data`;
- `DEMAND__TOTAL` appears in `target_codes`;
- each trained horizon has the required quantized `.h5` weights.

## 11. Run Prediction

Build the inference image:

```powershell
Set-Location $InferenceRepo
docker build -t predap-inference .
```

Run prediction for `DEMAND__TOTAL` using all available default horizons:

```powershell
$TrainingRuntime = Join-Path $TrainingRepo "private_runtime"

docker run --rm `
  -v "$TrainingRuntime\data:/app/data" `
  -v "$TrainingRuntime\quantized_models:/app/models" `
  -v "$TrainingRuntime\best_features:/app/best_features" `
  -v "$TrainingRuntime\results:/app/results" `
  -v "$TrainingRuntime\production_predictions:/app/output" `
  predap-inference `
  --input-directory /app/data/inference_daily.parquet `
  --old-input-directory /app/data/historical_daily.csv `
  --model-folder /app/models `
  --output-path /app/output/real/final_output_predictions `
  --metrics-df-path /app/output/production_evaluation_metrics.parquet `
  --diagnostic-covariates-path /app/best_features/BEST_features_NOSMOOTH_ `
  --model-selection-metrics-dir /app/results `
  --code DEMAND__TOTAL
```

Inspect outputs:

```powershell
Get-ChildItem "$TrainingRepo\private_runtime\production_predictions" -Recurse
Get-Content "$TrainingRepo\private_runtime\production_predictions\real\final_output_predictions_wide.csv" -TotalCount 10
```

The default prediction origin is the latest `timestamp` in
`inference_daily.parquet`. To inspect it before running:

```powershell
python -c "import pandas as pd; df=pd.read_parquet('private_runtime/data/inference_daily.parquet'); print(pd.to_datetime(df['timestamp']).max().date())"
```

To reproduce a specific old run, add:

```powershell
--prediction-origin-date YYYY-MM-DD
```

The operational file is
`private_runtime\production_predictions\real\final_output_predictions_wide.parquet`
plus the CSV copy. It has one row per future `timestamp`. The main column, for example
`DEMAND__TOTAL`, is the stitched prediction. Auxiliary columns show the
confidence interval, the horizon and the correction stage actually used for
that row:

- days 1-7 after the prediction origin use the 7-day model;
- days 8-14 use the 14-day model;
- days 15-30 use the 30-day model;
- days 31-60 use the 60-day model;
- days 61-182 use the 182-day model when available;
- days 183-365 use the 365-day model when available.

For each horizon, inference stops at the stage with the best saved WAPE:
`univariate`, `diagnostics` or `seasonal`. Inspect
`<CODE>__model_stage_reached`, `<CODE>__selected_stage_wape`,
`<CODE>__univariate_wape`, `<CODE>__diagnostics_wape` and
`<CODE>__seasonal_wape` in the wide CSV.

Log the generated prediction files to MLflow as artifacts:

```powershell
Set-Location $TrainingRepo
$env:INFERENCE_OUTPUT_PREFIX="real/final_output_predictions"

docker compose --profile mlflow-inference run --rm mlflow-inference-log

Remove-Item Env:\INFERENCE_OUTPUT_PREFIX -ErrorAction SilentlyContinue
```

In MLflow, open the `PREDAP_Inference_Outputs` experiment. The run contains
the raw long dataset, selected long file, wide Parquet file and wide CSV file.

For a daily production-style check, run one full week. Each origin date writes
its own folder and creates its own MLflow run:

```powershell
Set-Location $TrainingRepo
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

For the full real-code set, use the retrieval code list and enable parallel
shards. Start with 4 workers on a workstation; use 2 if memory or CPU is tight:

```powershell
Set-Location $TrainingRepo
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

The runner logs to MLflow only after each daily folder has been merged. During
the run, monitor Docker logs for shard progress.

Inspect:

```powershell
Get-Content "$TrainingRepo\private_runtime\production_predictions\real\daily\daily_inference_summary.csv"
Get-ChildItem "$TrainingRepo\private_runtime\production_predictions\real\daily" -Recurse -Filter final_output_predictions_wide.csv
```

## 12. Publish Clean GitHub Repositories

Run this only from the complete source bundle:

```powershell
Set-Location $SourceRoot

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\export_independent_repos.ps1 `
  -OutputRoot dist\github-repos `
  -Force `
  -RunSafetyCheck
```

Dry-run the publish:

```powershell
$Org = "guillemhg98"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 `
  -ReposRoot dist\github-repos `
  -RemoteBaseUrl https://github.com/$Org `
  -DryRun
```

Push:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 `
  -ReposRoot dist\github-repos `
  -RemoteBaseUrl https://github.com/$Org `
  -ForcePush `
  -Push
```

Use `-ForcePush` only for initial exported repositories that you are replacing
intentionally. It uses `git push --force-with-lease`.

## 13. Final Safety Rules

Before every push:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_github_safety.ps1 `
  -Path dist\github-repos
```

Never commit:

- `private_runtime/`;
- `runtime/`;
- `.env`;
- real `.csv`, `.xlsx`, `.parquet`, `.h5`, `.keras` or MLflow artifact files.

If GitHub Pages asks for login, the repository is private. Either log in with an
authorized GitHub account or make the repository public before sharing the
Pages URL.
