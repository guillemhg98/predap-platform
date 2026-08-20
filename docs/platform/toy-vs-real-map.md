# Toy vs Real Integration Map

This page maps every public toy step to the real private subprocess that
replaces it in production-like runs.

If you want commands rather than a conceptual map, start with
[Practical Runbook](../tutorials/practical-runbook.md).

## Rule of Thumb

The toy workflow proves public contracts. It does not run private data
connectors, real CCLR selection, TensorFlow training, model registry uploads or
daily production backfill logic.

Real subprocesses are supported through stable files and configurable paths.
Private adapters, real datasets, trained weights and production outputs must
stay outside Git.

## End-to-End Map

| Stage | Public toy implementation | Real/private implementation point | Required private artifact | Validation |
|---|---|---|---|---|
| Data retrieval | `examples/synthetic/predap_synthetic_workflow.py` writes a deterministic CSV. | Run an institutional connector or private adapter outside the public repo. | `private_runtime/data/historical_daily.parquet` and `private_runtime/data/target_codes_models_columns_order.json`. | `scripts/preflight_training.py` checks Parquet schema and code metadata before training. |
| CCLR feature selection | The toy workflow only creates target-code metadata. | Run `CCLR_PREDAP.main.CCLR_pipeline` privately or let training generate missing feature files when CCLR is available. | `private_runtime/best_features/BEST_features_NOSMOOTH_<CODE>.xlsx`. | Training loads the feature file for the target code and forecast. |
| Training | The toy workflow creates dummy moving-average JSON models. | Run `docker compose --profile train run --rm train-one`, `train-sweep` or `train-all`. | Private Parquet, code metadata and CCLR feature files. | Preflight checks, MLflow run logs and quantized model files. |
| Quantized model bundle | Dummy JSON files plus `manifest.json`. | `main_train_quantization.py` writes real model weights and updates `quantized_models/manifest.json`. | `private_runtime/quantized_models/`, `models_parameters/`, `transformer_outputs/`, `history/`. | `PREDAP_INFERENCE/production/validate_model_bundle.py --allow-real-data`. |
| Inference | The toy workflow writes synthetic prediction rows. | Run the standalone inference CLI with private mounted data, model weights and CCLR prefix. | Historical dataset, previous historical/diagnostics input, model folder, metrics path and output path. | Prediction table has the contract columns in `platform/module-contracts.md`. |
| Daily app backfill | Not covered by toy workflow. | Implement the daily input assembly step that merges latest real rows with previous predictions when source data is late. | Latest real history and previous prediction dataset. | Contract is documented in `PREDAP_INFERENCE/docs/prediction_pipeline_contract.md`. |
| Publication | Exported repos contain code, docs and synthetic fixtures. | Never publish real artifacts. | None. | `scripts/check_github_safety.ps1`. |

## Private Path Contract

Use `.env` to point Docker and scripts at private folders:

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

`HOST_*` values are host paths mounted into containers. `TRAIN_*` values are
paths as seen from inside the training container, whose working directory is
`/app`.

## Real Data Retrieval

The public repository only defines the output contract. A real connector should:

- authenticate and query the source system in a private environment;
- normalize to daily rows;
- write Parquet for training and inference;
- write the ordered JSON target-code list;
- keep raw extracts and intermediate files under private ignored storage.

Minimum historical dataset:

```text
timestamp,<CODE_1>,<CODE_2>,...
2024-01-01,123,45,...
```

The `timestamp` column must be parseable as a date or datetime. Every code in
`target_codes_models_columns_order.json` must exist as a numeric column.

## Real CCLR

Training expects a prefix, not a single file:

```text
runtime/best_features/BEST_features_NOSMOOTH_
```

For code `DEMAND__TOTAL`, the resolved file is:

```text
runtime/best_features/BEST_features_NOSMOOTH_DEMAND__TOTAL.xlsx
```

If the file is missing and `CCLR_PREDAP.main.CCLR_pipeline` is importable,
`main_train_quantization.py` attempts to generate it. For reproducible private
runs, precompute CCLR outputs and keep them in `private_runtime/best_features/`.
In standalone `predap-training`, CCLR is bundled under `predap-cclr/`. Override
`CCLR_REPO_PATH` only when testing another local CCLR checkout.

## Real Training

Before training, run:

```powershell
docker compose build
docker compose up -d postgres mlflow
docker compose --profile train run --rm train-one
```

For all configured codes and horizons:

```powershell
docker compose --profile all run --rm train-all
```

The preflight step checks:

- Parquet file exists;
- codes JSON exists and is a non-empty list;
- all codes exist in the Parquet schema;
- the selected target code exists;
- the CCLR output directory is writable;
- TensorFlow imports;
- GPU visibility when `TRAIN_REQUIRE_GPU_FLAG=--require-gpu`;
- `CCLR_PREDAP.main.CCLR_pipeline` imports.

## Real Inference

Validate private model artifacts before inference:

```powershell
python PREDAP_INFERENCE/production/validate_model_bundle.py --model-folder private_runtime/quantized_models --allow-real-data
```

Run the standalone inference entrypoint with private mounts:

```bash
docker run --rm \
  -v "$PWD/private_runtime/data:/app/data" \
  -v "$PWD/private_runtime/quantized_models:/app/models" \
  -v "$PWD/private_runtime/best_features:/app/best_features" \
  -v "$PWD/private_runtime/results:/app/results" \
  -v "$PWD/private_runtime/production_predictions:/app/output" \
  predap-inference \
  --input-directory /app/data/historical_daily.parquet \
  --old-input-directory /app/data/historical_daily.csv \
  --model-folder /app/models \
  --output-path /app/output/real/final_output_predictions \
  --metrics-df-path /app/output/production_evaluation_metrics.parquet \
  --diagnostic-covariates-path /app/best_features/BEST_features_NOSMOOTH_ \
  --model-selection-metrics-dir /app/results
```

Use `--code <CODE>` one or more times to restrict inference to selected codes.
If no code is provided, the pipeline discovers codes from the input dataset.

## Current Implementation Status

Implemented and public:

- deterministic synthetic end-to-end workflow;
- data, model bundle and prediction contracts;
- model bundle validator;
- training preflight checks;
- Docker profiles for MLflow, PostgreSQL and training;
- standalone inference CLI;
- export and safety-check scripts for public Git repositories.

Implemented but private-runtime only:

- real data ingestion adapters;
- real CCLR feature generation over institutional data;
- TensorFlow training and quantization;
- production prediction outputs.

Contemplated but not fully hardened in this public repo:

- daily input assembly that backfills missing real history with previous
  predictions until source data arrives;
- private model registry integration;
- private orchestration around institutional authentication and scheduling.
