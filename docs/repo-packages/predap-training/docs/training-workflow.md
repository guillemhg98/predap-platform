# Training Workflow

## Inputs

From `predap-data-retrieval`:

- historical daily dataset;
- target-code metadata.

From bundled `predap-cclr/`:

- diagnostic covariate feature files.

## Public Toy Workflow

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
```

This produces a dummy model bundle. It does not train TensorFlow models.
It validates the model-bundle contract only.

## Private Real Workflow

1. Mount private data into ignored runtime paths.
2. Start MLflow and PostgreSQL.
3. Run preflight checks.
4. Train one code or all configured codes.
5. Quantize and export private model bundles.
6. Validate the bundle from `predap-inference`.

Configure these values in `.env`:

```text
TRAIN_DATA_PATH=private_runtime/data/historical_daily.parquet
TRAIN_ALL_CODES_PATH=private_runtime/data/target_codes_models_columns_order.json
TRAIN_BEST_FEATURES_PREFIX=runtime/best_features/BEST_features_NOSMOOTH_
```

Default service ports are:

```text
MLFLOW_HOST_PORT=55001
POSTGRES_HOST_PORT=55433
```

If a `BEST_features_NOSMOOTH_<CODE>.xlsx` file is missing, training can compute
it through the bundled `predap-cclr/` folder. Docker already sets
`CCLR_REPO_PATH=/app/predap-cclr`. Do not use `--require-best-features` when
you intentionally want training to create those files.

```powershell
docker compose build
docker compose up -d postgres mlflow
docker compose --profile all run --rm train-all
```

Standalone packaging changes do not alter epochs, learning rate, architecture,
horizons or other Hydra training defaults. Those values remain controlled by
the config files under `conf/` and any explicit command overrides.

## Import Recovered Models into MLflow

If old model artifacts have been copied into the private runtime folders, log
them to MLflow without retraining:

```powershell
$env:IMPORT_MODEL_CODE="DEMAND__TOTAL"
$env:IMPORT_SOURCE_LABEL="recovered_from_predap_production_simplified"
docker compose --profile mlflow-import run --rm mlflow-import
Remove-Item Env:\IMPORT_MODEL_CODE
Remove-Item Env:\IMPORT_SOURCE_LABEL
```

Open the `PREDAP_Recovered_Artifacts` experiment in MLflow. Each run represents
one recovered forecast/lookback pair and contains quantized weights, parameters,
full Keras models, training histories, best-features files and the manifest when
present.

## Outputs

Keep these private:

- `runtime/mlflow/`
- `runtime/quantized_models/`
- `runtime/models_parameters/`
- `runtime/transformer_outputs/`
- `runtime/history/`
