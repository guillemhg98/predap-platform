# Toy Data Workflow

The toy workflow is the public way to prove PREDAP works without real data.
It is a contract smoke test, not a substitute for real data ingestion, CCLR or
TensorFlow training.

## Run

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
python PREDAP_INFERENCE/production/validate_model_bundle.py --model-folder runtime/synthetic_demo/model_bundle
```

If you are working from independent GitHub repositories, run the workflow from
`predap-platform` and validate with the sibling `predap-inference` repository:

```powershell
$Workspace = (Get-Location).Path
$PlatformRepo = Join-Path $Workspace "predap-platform"
$InferenceRepo = Join-Path $Workspace "predap-inference"
Set-Location $PlatformRepo
python examples\synthetic\predap_synthetic_workflow.py --output-dir runtime\synthetic_demo
python "$InferenceRepo\production\validate_model_bundle.py" --model-folder "$PlatformRepo\runtime\synthetic_demo\model_bundle"
```

## Read the Generated Outputs

The toy workflow writes a small local run under `runtime/synthetic_demo/`.
Those files are ignored by Git and are safe to delete and regenerate.

```powershell
Get-ChildItem runtime\synthetic_demo -Recurse
Get-Content runtime\synthetic_demo\retrieval_export\historical_daily.csv -TotalCount 5
Get-Content runtime\synthetic_demo\retrieval_export\target_codes_models_columns_order.json
Get-Content runtime\synthetic_demo\model_bundle\manifest.json
Get-Content runtime\synthetic_demo\inference\predictions.csv -TotalCount 10
Get-Content runtime\synthetic_demo\metrics.json
```

What each artifact means:

| Artifact | What it proves | Real equivalent |
|---|---|---|
| `retrieval_export/historical_daily.csv` | The platform can consume a daily time-series table with `timestamp` plus target-code columns. | `private_runtime/data/historical_daily.parquet` produced by the private data connector. |
| `retrieval_export/target_codes_models_columns_order.json` | Training and inference agree on the target-code list and ordering. | `private_runtime/data/target_codes_models_columns_order.json`. |
| `retrieval_export/models_columns_orders.txt` | Legacy/plain-text view of the same target-code ordering. | Private metadata exported by the real data preparation step, if needed. |
| `model_bundle/manifest.json` | The model bundle declares schema, target codes, horizons and whether it contains real data. | `private_runtime/quantized_models/manifest.json` written by real quantized training. |
| `model_bundle/models/<CODE>/*.json` | Dummy model files exist for every code and horizon. | Real `.h5` quantized weights under `<CODE>/<model_type>/...`. |
| `inference/predictions.csv` | The prediction table has the production columns expected by downstream consumers. | Private production prediction output. |
| `metrics.json` | The run can report a basic evaluation summary without private ML dependencies. | MLflow metrics and private evaluation artifacts. |

## What Happens Step by Step

1. `generate_history()` creates deterministic synthetic daily values for each
   target code.
2. The script splits the rows into train and holdout windows.
3. It writes the retrieval export that stands in for the real data retrieval
   subprocess.
4. `evaluate_holdout()` calculates dummy MAE and RMSE so the metrics contract
   can be inspected.
5. `write_model_bundle()` creates deterministic moving-average JSON models and
   a public `manifest.json`.
6. `write_predictions()` writes the production-shaped prediction table.
7. `validate_model_bundle.py` verifies the model bundle contract.

This is intentionally transparent and lightweight. It shows file contracts and
handoffs, not model quality.

## What It Covers

| Platform step | Toy implementation |
|---|---|
| Data retrieval | deterministic synthetic daily time series |
| CCLR/training metadata | synthetic target-code JSON |
| Model training | deterministic dummy moving-average models |
| Model bundle | JSON model files plus `manifest.json` |
| Inference | prediction table with production columns |

## What It Does Not Cover

- TensorFlow training;
- MLflow run logging;
- real CCLR feature selection;
- private data connectors;
- production model registry integration.

Those are private-runtime concerns. The toy workflow exists to validate public
contracts and documentation.

See [Toy vs Real Integration Map](../platform/toy-vs-real-map.md) for the exact
replacement point for each real subprocess.
