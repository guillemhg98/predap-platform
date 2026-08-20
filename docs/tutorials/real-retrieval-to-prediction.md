# Real Retrieval Output to Prediction

This tutorial starts after the data-retrieval module has already produced the
real joined demand/diagnosis files. It shows how to move those private outputs
into the ignored runtime area, train and quantize Transformer models with
MLflow, validate the model bundle, and run prediction.

Real data, CCLR feature files, trained weights, MLflow artifacts and prediction
outputs must stay outside Git.

If you are starting from a fresh GitHub clone, first read
[Private Runtime Setup](../platform/private-runtime-setup.md). It defines the
folders to create, what to download from private storage and the required
schemas for time series, aggregation metadata, CCLR files and model artifacts.

## 0. Inputs Produced by Data Retrieval

The retrieval output folder should contain a `finals/` directory with files
like these:

```text
finals/
  demand_diagnosis_joined.parquet
  demand_diagnosis_joined.csv
  demand_diagnosis_joined_training_until_YYYY-MM-DD_no_imputed.parquet
  target_codes_models_columns_order.json
  models_columns_orders.txt
```

Recommended use:

| File | Used for |
|---|---|
| `demand_diagnosis_joined_training_until_YYYY-MM-DD_no_imputed.parquet` | Training and quantization. |
| `demand_diagnosis_joined.parquet` | Production-style inference input. |
| `demand_diagnosis_joined.csv` | Historical CSV required by the diagnostics branch during inference. |
| `target_codes_models_columns_order.json` | Ordered list of target codes to train. |

For the current local private dataset, the retrieval finals folder is:

```powershell
$RetrievalFinals = "D:\TRANSFORMERS_PREDAP-predap_production_simplified\TRANSFORMERS_PREDAP-predap_production_simplified\AQUAS_DATA_RETRIEVAL-git\data\data\finals"
```

For another machine, replace `$RetrievalFinals` with the equivalent private
retrieval output path.

## 1. Prepare the Private Runtime Area

Run this from the complete PREDAP source workspace, next to
`docker-compose.yml`:

```powershell
$Repo = (Get-Location).Path
$RetrievalFinals = "D:\TRANSFORMERS_PREDAP-predap_production_simplified\TRANSFORMERS_PREDAP-predap_production_simplified\AQUAS_DATA_RETRIEVAL-git\data\data\finals"

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

Copy the real retrieval artifacts into ignored runtime storage:

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

Check the private files:

```powershell
Get-ChildItem private_runtime\data
Get-Content private_runtime\data\target_codes_models_columns_order.json -TotalCount 20
```

## 2. Configure `.env`

Create the local environment file:

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

Make sure `.env` contains these values:

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
TRAIN_REQUIRE_GPU_FLAG=--require-gpu

INFERENCE_EXPERIMENT_NAME=PREDAP_Inference_Outputs
INFERENCE_OUTPUT_PREFIX=real/final_output_predictions
INFERENCE_PREDICTION_ORIGIN_DATE=
INFERENCE_METRICS_PATH=
INFERENCE_MODEL_SELECTION_METRICS_DIR=private_runtime/results
```

If you are testing on a machine without GPU, set:

```text
TRAIN_REQUIRE_GPU_FLAG=
```

Real training is still expected to run on a GPU-capable environment.

Validate Compose configuration:

```powershell
docker compose config
```

If Docker reports that `127.0.0.1:5433` or `127.0.0.1:5001` is already
allocated, either stop the older containers or change the host ports in `.env`.

Inspect running containers:

```powershell
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"
```

Option A, stop older PREDAP support services if you no longer need them:

```powershell
docker stop predap-mlflow-1 predap-postgres-1
```

Option B, keep the older services and use different ports for this workspace:

```text
POSTGRES_HOST_PORT=5434
MLFLOW_HOST_PORT=5002
```

Then open MLflow at `http://127.0.0.1:5002` instead of port `5001`.

## 3. Inspect the Real Retrieval Contract

Use Python to check that the Parquet and JSON agree:

```powershell
python -c "import json, pyarrow.parquet as pq; from pathlib import Path; p=Path('private_runtime/data/historical_daily.parquet'); c=Path('private_runtime/data/target_codes_models_columns_order.json'); s=pq.read_schema(p); codes=json.loads(c.read_text(encoding='utf-8-sig')); print('columns', len(s.names)); print('codes', len(codes)); print('first_codes', codes[:10]); print('missing', [x for x in codes if x not in s.names][:10])"
```

Expected:

- column `timestamp` exists;
- all codes in the JSON exist as numeric columns in the Parquet;
- `missing` is an empty list.

For the current dataset, the first valid smoke-test code is:

```text
DEMAND__TOTAL
```

## 4. Run Training Preflight

Local preflight:

```powershell
python scripts\preflight_training.py `
  --data-path private_runtime\data\historical_daily.parquet `
  --codes-path private_runtime\data\target_codes_models_columns_order.json `
  --target-code DEMAND__TOTAL `
  --best-features-prefix private_runtime\best_features\BEST_features_NOSMOOTH_
```

Inside Docker, the training services run the same preflight before training.

CCLR note: if
`private_runtime\best_features\BEST_features_NOSMOOTH_DEMAND__TOTAL.xlsx` does
not exist, `main_train_quantization.py` attempts to generate it through
`CCLR_PREDAP.main.CCLR_pipeline`. For reproducible production runs, precompute
and keep those Excel files under `private_runtime\best_features\`.

## 5. Start MLflow

```powershell
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

Follow logs:

```powershell
docker compose logs -f mlflow
```

Do not continue to model validation or inference until `docker compose ps`
shows `mlflow` running and the training command has finished successfully.

## 6. Import Recovered Models into MLflow

If you copied old model artifacts into `private_runtime`, they are available to
inference but MLflow will not show them until they are logged as runs. Import
them into a dedicated MLflow experiment:

```powershell
$env:IMPORT_MODEL_CODE="DEMAND__TOTAL"
$env:IMPORT_SOURCE_LABEL="recovered_from_predap_production_simplified"

docker compose --profile mlflow-import run --rm mlflow-import

Remove-Item Env:\IMPORT_MODEL_CODE
Remove-Item Env:\IMPORT_SOURCE_LABEL
```

Open MLflow and select the `PREDAP_Recovered_Artifacts` experiment. You should
see one run per recovered horizon/lookback pair, with artifacts grouped under:

- `quantized_weights`
- `model_parameters`
- `keras_models`
- `history`
- `best_features`
- `manifest`

For a dry run without writing to MLflow:

```powershell
$env:IMPORT_MODEL_CODE="DEMAND__TOTAL"
docker compose --profile mlflow-import run --rm mlflow-import `
  python scripts/import_recovered_models_to_mlflow.py --dry-run
Remove-Item Env:\IMPORT_MODEL_CODE
```

## 7. Smoke Train One Code and One Horizon

This is the fastest real-data check. It trains and quantizes only
`DEMAND__TOTAL` with setup `7_7`.

```powershell
$env:TRAIN_TARGET_CODE="DEMAND__TOTAL"
$env:TRAIN_EXPERIMENT_SETUP="7_7"

docker compose --profile train run --rm train-one
```

Refresh MLflow and confirm that the run contains parameters, metrics and
artifacts.

Check generated private artifacts:

```powershell
Get-ChildItem private_runtime\best_features -Recurse
Get-ChildItem private_runtime\quantized_models -Recurse
Get-ChildItem private_runtime\models_parameters -Recurse
Get-ChildItem private_runtime\transformer_outputs -Recurse
Get-ChildItem private_runtime\history -Recurse
```

## 8. Train Missing Long Horizons

The recovered local bundle already contains the copied short horizons. Train the
missing long horizons from the same code and data:

```powershell
$env:TRAIN_TARGET_CODE="DEMAND__TOTAL"

$env:TRAIN_EXPERIMENT_SETUP="182_182"
docker compose --profile train run --rm train-one

$env:TRAIN_EXPERIMENT_SETUP="365_182"
docker compose --profile train run --rm train-one

Remove-Item Env:\TRAIN_TARGET_CODE
Remove-Item Env:\TRAIN_EXPERIMENT_SETUP
```

Refresh MLflow after each run. The newly trained runs are logged by
`main_train_quantization.py`; the recovered short-horizon runs remain under
`PREDAP_Recovered_Artifacts`.

## 9. Validate the Quantized Model Bundle

Run this only after training has finished. If
`private_runtime\quantized_models\manifest.json` does not exist, training did
not complete and there is no real model bundle to validate yet.

```powershell
python PREDAP_INFERENCE\production\validate_model_bundle.py `
  --model-folder private_runtime\quantized_models `
  --allow-real-data
```

Expected:

- the manifest is accepted with `--allow-real-data`;
- the trained code appears in `target_codes`;
- required model types are present.

## 10. Run Prediction for the Smoke-Test Horizon

Run inference only after the model bundle validator passes.

If you trained only `7_7`, restrict inference to the same horizon:

```powershell
docker build -t predap-inference .\PREDAP_INFERENCE

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
  --output-path /app/output/smoke/smoke_final_output_predictions `
  --metrics-df-path /app/output/production_evaluation_metrics.parquet `
  --diagnostic-covariates-path /app/best_features/BEST_features_NOSMOOTH_ `
  --model-selection-metrics-dir /app/results `
  --code DEMAND__TOTAL `
  --lookback-list 7 `
  --forecast-list 7
```

Inspect prediction outputs:

```powershell
Get-ChildItem private_runtime\production_predictions -Recurse
Get-Content private_runtime\production_predictions\smoke\smoke_final_output_predictions_wide.csv -TotalCount 10
```

For this smoke test, the prediction origin is the latest `timestamp` in
`private_runtime\data\inference_daily.parquet`. The wide output should start
one day after that origin and contain 7 future rows for `DEMAND__TOTAL`.

Inspect the default origin:

```powershell
python -c "import pandas as pd; df=pd.read_parquet('private_runtime/data/inference_daily.parquet'); print(pd.to_datetime(df['timestamp']).max().date())"
```

To reproduce a specific old run, add:

```powershell
--prediction-origin-date YYYY-MM-DD
```

Log the smoke prediction outputs to MLflow:

```powershell
$env:INFERENCE_OUTPUT_PREFIX="smoke/smoke_final_output_predictions"

docker compose --profile mlflow-inference run --rm mlflow-inference-log

Remove-Item Env:\INFERENCE_OUTPUT_PREFIX -ErrorAction SilentlyContinue
```

Open the `PREDAP_Inference_Outputs` experiment in MLflow to inspect the raw
long output, selected long file, wide Parquet file and wide CSV copy.

## 11. Train a Small Batch

After the single-code smoke test passes, train two configured codes across the
configured experiment setups:

```powershell
$env:TRAIN_ALL_LIMIT="2"
docker compose --profile all run --rm train-all
Remove-Item Env:\TRAIN_ALL_LIMIT
```

Validate again:

```powershell
python PREDAP_INFERENCE\production\validate_model_bundle.py `
  --model-folder private_runtime\quantized_models `
  --allow-real-data
```

## 12. Full Private Run

Run all configured codes and experiment setups:

```powershell
docker compose --profile all run --rm train-all
```

Then run inference without restricting `--code` if you want all discoverable
codes, or repeat `--code <CODE>` to select a subset.

For all default horizons, omit the smoke-test horizon overrides:

```powershell
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
  --model-selection-metrics-dir /app/results
```

The main operational output is
`private_runtime\production_predictions\real\final_output_predictions_wide.parquet`
with a CSV copy at
`private_runtime\production_predictions\real\final_output_predictions_wide.csv`.
It has one row per future date and one main prediction column per target code.
The columns ending in `__forecast`, `__lookback`, `__model_id` and
`__model_stage_reached` show which horizon and correction stage were used for
each day. `__selected_stage_wape`, `__univariate_wape`,
`__diagnostics_wape` and `__seasonal_wape` show why the pipeline stopped there.

To log this full run to MLflow:

```powershell
$env:INFERENCE_OUTPUT_PREFIX="real/final_output_predictions"

docker compose --profile mlflow-inference run --rm mlflow-inference-log

Remove-Item Env:\INFERENCE_OUTPUT_PREFIX -ErrorAction SilentlyContinue
```

## 13. Daily Inference with One MLflow Run per Day

For production-style operation, run inference once per prediction origin date.
The daily wrapper creates separated folders and logs each day as an independent
MLflow run.

This command runs the latest 7 available origin dates in
`private_runtime\data\inference_daily.parquet`:

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

For a full real run with every trained target code, use the retrieval code
metadata file and parallel code shards:

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

Each shard writes temporary files below `_shards/`; after all shards finish the
runner merges them into the standard daily wide and selected-long outputs and
then creates the MLflow run.

To reproduce a specific week, set explicit dates before running:

```powershell
$env:DAILY_INFERENCE_START_DATE="YYYY-MM-DD"
$env:DAILY_INFERENCE_END_DATE="YYYY-MM-DD"
docker compose --profile daily-inference run --rm daily-inference
Remove-Item Env:\DAILY_INFERENCE_START_DATE -ErrorAction SilentlyContinue
Remove-Item Env:\DAILY_INFERENCE_END_DATE -ErrorAction SilentlyContinue
```

Inspect the daily files:

```powershell
Get-Content private_runtime\production_predictions\real\daily\daily_inference_summary.csv
Get-ChildItem private_runtime\production_predictions\real\daily -Recurse -Filter final_output_predictions_wide.csv
Get-Content private_runtime\production_predictions\real\daily\YYYY-MM-DD\final_output_predictions_wide.csv -TotalCount 10
```

Open MLflow and inspect the `PREDAP_Inference_Outputs` experiment. You should
see one run named `daily_inference_YYYY-MM-DD` for each origin date.

## 14. Stop Services

```powershell
docker compose down
```

Keep `private_runtime/` and `runtime/` private. Do not copy those folders into
GitHub repositories.
