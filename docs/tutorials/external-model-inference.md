# External Model Inference

PREDAP inference can run with models produced by the training module or with
models uploaded from another environment, provided the model bundle contract is
respected.

## 1. Prepare the Bundle

```text
model_bundle/
  manifest.json
  models/
    DEMAND__TOTAL/
      forecast_7_lookback_7.h5
      forecast_14_lookback_14.h5
```

For a public smoke test, JSON dummy models are accepted. For production, use the
runtime formats supported by the inference code.

## 2. Validate Before Running

```powershell
python PREDAP_INFERENCE/production/validate_model_bundle.py --model-folder path/to/model_bundle
```

If the bundle contains real-data-derived weights, keep it private and do not
commit it to GitHub.

## 3. Run Inference

Mount the private model bundle and the private historical dataset into the
inference container. Mount CCLR feature files separately so they do not have to
live beside the historical dataset:

```bash
docker run --rm \
  -v "$PWD/private_data:/app/data" \
  -v "$PWD/private_models:/app/models" \
  -v "$PWD/private_best_features:/app/best_features" \
  -v "$PWD/private_results:/app/results" \
  -v "$PWD/output:/app/output" \
  predap-inference \
  --input-directory /app/data/demand_diagnostics_joined.parquet \
  --old-input-directory /app/data/finals_combined.csv \
  --model-folder /app/models \
  --output-path /app/output/real/final_output_predictions \
  --metrics-df-path /app/output/production_evaluation_metrics.parquet \
  --diagnostic-covariates-path /app/best_features/BEST_features_NOSMOOTH_ \
  --model-selection-metrics-dir /app/results
```

By default, inference uses the latest timestamp available in the input file.
Pass `--prediction-origin-date YYYY-MM-DD` only to reproduce or test a specific
origin date.

The main operational output is:

```text
/app/output/real/final_output_predictions_wide.parquet
/app/output/real/final_output_predictions_wide.csv
```

The wide output includes `<CODE>__model_stage_reached` and the WAPE columns
used to decide whether the forecast stopped at `univariate`, `diagnostics` or
`seasonal`.

It starts at X+1 and has one row per predicted day. The main columns are the
target codes. Columns ending in `__forecast`, `__lookback`, `__horizon_day` and
`__model_id` explain which trained model produced each row.
