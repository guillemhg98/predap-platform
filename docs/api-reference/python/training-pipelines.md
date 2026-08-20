# Training Pipelines

The training repository owns the full private model training path.

## Public Smoke Path

The public CI workflow uses the synthetic dummy workflow:

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
```

This checks artifact contracts without importing TensorFlow.

## Private Training Path

Real training requires private data and runtime directories:

```text
TRAIN_DATA_PATH=private_runtime/data/historical_daily.parquet
TRAIN_ALL_CODES_PATH=private_runtime/data/target_codes_models_columns_order.json
TRAIN_BEST_FEATURES_PREFIX=runtime/best_features/BEST_features_NOSMOOTH_
```

```powershell
docker compose up -d postgres mlflow
$env:TRAIN_TARGET_CODE="<CODE>"
$env:TRAIN_EXPERIMENT_SETUP="7_7"
docker compose --profile train run --rm train-one
```

`scripts/preflight_training.py` receives the same paths as
`main_train_quantization.py`, so schema checks and training use the same private
artifacts.

Batch training:

```powershell
docker compose --profile all run --rm train-all
```

## Main Entrypoints

- `main_train.py`
- `main_train_quantization.py`
- `scripts/train_all_codes.py`
- `scripts/preflight_training.py`

## Outputs

Private outputs should remain in ignored runtime paths:

- quantized model weights;
- MLflow runs and artifacts;
- model parameters;
- history and metrics files.
