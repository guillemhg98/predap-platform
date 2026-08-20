# Synthetic End-to-End Tutorial

This tutorial validates the public PREDAP workflow without private data.

## 1. Generate Dummy Data, Dummy Models and Dummy Predictions

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
```

The workflow creates:

```text
runtime/synthetic_demo/retrieval_export/historical_daily.csv
runtime/synthetic_demo/retrieval_export/target_codes_models_columns_order.json
runtime/synthetic_demo/model_bundle/manifest.json
runtime/synthetic_demo/inference/predictions.csv
runtime/synthetic_demo/inference/predictions_wide.csv
runtime/synthetic_demo/metrics.json
```

Inspect the generated contracts:

```powershell
Get-Content runtime\synthetic_demo\retrieval_export\historical_daily.csv -TotalCount 5
Get-Content runtime\synthetic_demo\retrieval_export\target_codes_models_columns_order.json
Get-Content runtime\synthetic_demo\model_bundle\manifest.json
Get-Content runtime\synthetic_demo\inference\predictions.csv -TotalCount 10
Get-Content runtime\synthetic_demo\inference\predictions_wide.csv -TotalCount 10
Get-Content runtime\synthetic_demo\metrics.json
```

The synthetic workflow does not log to MLflow. MLflow starts at the real
training step, because only the Docker training profiles run the Transformer
training and quantization code.

## 2. Validate the Model Bundle

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

The command should print the schema version, target codes and model counts.

## 3. Inspect the Prediction Contract

Open:

```text
runtime/synthetic_demo/inference/predictions.csv
```

`predictions.csv` is the raw long audit table. Every row follows the production
prediction table contract:

- target code;
- target date;
- forecast origin and final forecast date;
- horizon and lookback;
- prediction;
- confidence interval;
- velocity and acceleration.

`predictions_wide.csv` is the operational view. It has one row per future
`timestamp`, one main prediction column per target code and auxiliary columns
such as `<CODE>__ci_lower`, `<CODE>__ci_upper`, `<CODE>__forecast`,
`<CODE>__lookback`, `<CODE>__horizon_day`, `<CODE>__model_id` and
`<CODE>__model_stage_reached`.

With the default toy setup, days 1-7 use the 7-day dummy model, days 8-14 use
the 14-day dummy model, and days 15-30 use the 30-day dummy model.
The synthetic workflow also fills WAPE-audit columns so the public tutorial
shows where to inspect stage-aware inference decisions before using real data.

## 4. Use the Same Contract in Production

Replace the synthetic retrieval export with private data mounted outside Git,
replace the dummy JSON models with private trained model weights and keep the
same module boundaries.
