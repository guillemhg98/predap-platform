# 5-Minute Quickstart

This quickstart validates PREDAP without private healthcare data.
It uses the toy workflow only; real data and real subprocesses are covered in
[Practical Runbook](../tutorials/practical-runbook.md).

Use this page when you want a fast public smoke test. Use the runbook when you
want the complete path with real retrieval outputs, MLflow, recovered models,
training and prediction.

This toy smoke test does not require TensorFlow. If `py -3.12` is not available
on Windows, use `python` or an explicit Python executable. For real training or
full inference dependency installs, use Python 3.10-3.12 or Docker; Python 3.13
is not compatible with the currently pinned TensorFlow range.

When moving from this toy quickstart to real data, start with
[Private Runtime Setup](../platform/private-runtime-setup.md). It explains what
to download after cloning GitHub and where to place every private folder.

## 1. Run the Synthetic Workflow

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
```

This generates:

- a synthetic historical daily dataset;
- target-code metadata;
- a dummy model bundle;
- synthetic prediction rows;
- dummy validation metrics.

## 2. Validate the Dummy Model Bundle

In the complete source workspace:

```powershell
python PREDAP_INFERENCE/production/validate_model_bundle.py --model-folder runtime/synthetic_demo/model_bundle
```

With independent GitHub repositories cloned as siblings:

```powershell
$Workspace = (Get-Location).Path
$PlatformRepo = Join-Path $Workspace "predap-platform"
$InferenceRepo = Join-Path $Workspace "predap-inference"
python "$InferenceRepo\production\validate_model_bundle.py" --model-folder "$PlatformRepo\runtime\synthetic_demo\model_bundle"
```

Expected result: the command prints the bundle schema, target codes and number
of model files per code.

## 3. Inspect the Outputs

```text
runtime/synthetic_demo/retrieval_export/historical_daily.csv
runtime/synthetic_demo/retrieval_export/target_codes_models_columns_order.json
runtime/synthetic_demo/model_bundle/manifest.json
runtime/synthetic_demo/inference/predictions.csv
runtime/synthetic_demo/metrics.json
```

These files are generated locally and ignored by Git.

Useful inspection commands:

```powershell
Get-Content runtime\synthetic_demo\retrieval_export\historical_daily.csv -TotalCount 5
Get-Content runtime\synthetic_demo\model_bundle\manifest.json
Get-Content runtime\synthetic_demo\inference\predictions.csv -TotalCount 10
Get-Content runtime\synthetic_demo\metrics.json
```

The toy workflow is deliberately not an MLflow run. It explains and validates
the public file contracts. MLflow is exercised by the real training stack in
the next section.

## 4. Start the Real Training Stack

Real training requires private data mounted locally and `.env` values for
`TRAIN_DATA_PATH`, `TRAIN_ALL_CODES_PATH` and `TRAIN_BEST_FEATURES_PREFIX`.

```powershell
Copy-Item .env.example .env
docker compose build
docker compose up -d postgres mlflow
```

Open MLflow with the configured host port:

```powershell
$MlflowPort = ((Select-String -Path .env -Pattern '^MLFLOW_HOST_PORT=').Line -split '=', 2)[1]
$MlflowUrl = "http://127.0.0.1:$MlflowPort"
Start-Process $MlflowUrl
```

Train one code:

```powershell
$env:TRAIN_TARGET_CODE="DEMAND__TOTAL"
$env:TRAIN_EXPERIMENT_SETUP="7_7"
docker compose --profile train run --rm train-one
```

## 5. Next Steps

- Follow [Practical Runbook](../tutorials/practical-runbook.md).
- Read [Repository Strategy](../platform/repository-strategy.md).
- Read [Data Policy](../platform/data-policy.md).
- Follow [External Model Inference](../tutorials/external-model-inference.md).
