# Real Data Private Workflow

This tutorial describes how to run PREDAP with real data while keeping GitHub
clean.

Use this page together with the
[Toy vs Real Integration Map](../platform/toy-vs-real-map.md), which marks what
is implemented publicly, what must run privately and what is only contemplated
as a production hardening step.

For a more guided copy-paste path, start with
[Practical Runbook](practical-runbook.md).

If you already have the real `AQUAS_DATA_RETRIEVAL-git/data/data/finals`
outputs, follow
[Real Retrieval Output to Prediction](real-retrieval-to-prediction.md) for the
copy-paste command sequence from retrieval artifacts to final predictions.

## 1. Keep Private Files Outside Git

Use an ignored folder such as:

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
  history/
  production_predictions/
    real/
    smoke/
```

Do not place real files under `examples/` or any tracked docs folder.

## 2. Required Real Data Inputs

Historical dataset:

```text
timestamp,<CODE_1>,<CODE_2>,...
2024-01-01,123,45,...
```

Production format should be Parquet. CSV is useful for manual inspection but
must remain private if it contains real data.

Code metadata:

```json
[
  "DEMAND__TOTAL",
  "SERVEI_CODI__URG"
]
```

CCLR feature files:

```text
BEST_features_NOSMOOTH_<CODE>.xlsx
```

## 3. Configure Paths

```powershell
Copy-Item .env.example .env
```

Edit `.env` so all host paths point to private folders.

Minimum private values:

```text
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

`HOST_*` paths are host paths mounted by Docker. `TRAIN_*` paths are read inside
the training container from `/app`.

## 4. Run Data Retrieval

The public `predap-data-retrieval` repo defines the schema contract. Private
institutional connectors should run outside the public repository and export:

```text
private_runtime/data/historical_daily.parquet
private_runtime/data/target_codes_models_columns_order.json
```

The training preflight currently expects the real training table to be Parquet.
Keep CSV copies private and use them only for inspection or inference inputs
that explicitly need CSV.

## 5. Run CCLR

Run CCLR in a private environment and write feature files to:

```text
private_runtime/best_features/
```

Training resolves each file from `TRAIN_BEST_FEATURES_PREFIX`. For example,
`TRAIN_BEST_FEATURES_PREFIX=runtime/best_features/BEST_features_NOSMOOTH_` and
code `DEMAND__TOTAL` resolve to
`runtime/best_features/BEST_features_NOSMOOTH_DEMAND__TOTAL.xlsx` inside the
container.

## 6. Train and Quantize

```powershell
docker compose build
docker compose up -d postgres mlflow
docker compose ps
$MlflowPort = ((Select-String -Path .env -Pattern '^MLFLOW_HOST_PORT=').Line -split '=', 2)[1]
$MlflowUrl = "http://127.0.0.1:$MlflowPort"
Invoke-WebRequest "$MlflowUrl/health"
Start-Process $MlflowUrl
$env:TRAIN_TARGET_CODE="<CODE>"
$env:TRAIN_EXPERIMENT_SETUP="7_7"
docker compose --profile train run --rm train-one
```

The preflight step checks the Parquet schema, JSON code list, selected code,
feature directory write access, TensorFlow import, GPU visibility when required
and CCLR import.

MLflow is available at:

Refresh MLflow in the browser opened above.

After `train-one` finishes, refresh MLflow and inspect parameters, metrics and
artifacts for the run.

For all configured codes:

```powershell
$env:TRAIN_ALL_LIMIT="2"
docker compose --profile all run --rm train-all
Remove-Item Env:\TRAIN_ALL_LIMIT
docker compose --profile all run --rm train-all
```

The first command limits the batch to two codes. The second command runs all
configured codes after the small batch has passed.

## 7. Validate Models and Run Inference

```powershell
python PREDAP_INFERENCE/production/validate_model_bundle.py --model-folder private_runtime/quantized_models --allow-real-data
```

Then run inference with private mounted paths as described in
[External Model Inference](external-model-inference.md).

Daily backfill with previous predictions is documented as a contract in
`PREDAP_INFERENCE/docs/prediction_pipeline_contract.md`; it is contemplated but
not fully hardened in this public repo.

## 8. Publish Safely

Before pushing:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_github_safety.ps1 -Path dist\github-repos
```
