# Module Contracts

The platform stays modular by exchanging files with stable schemas.

## Historical Dataset

Owner: `predap-data-retrieval`

Required:

- `timestamp`
- one numeric column per target code

Recommended production format: Parquet.

Recommended public tutorial format: CSV.

For real training, the current preflight expects Parquet and verifies that every
code in the metadata file exists in the dataset schema.

Private runtime names:

| File | Purpose |
|---|---|
| `private_runtime/data/historical_daily.parquet` | Training and quantization time series. |
| `private_runtime/data/inference_daily.parquet` | Production-style inference time series. |
| `private_runtime/data/historical_daily.csv` | CSV historical view required by the diagnostics branch during inference. |

All three files must keep identical target-code column names.

## Target Code Metadata

Owner: `predap-data-retrieval`

`target_codes_models_columns_order.json` contains the ordered list of modeled
target columns.

Private runtime name:

```text
private_runtime/data/target_codes_models_columns_order.json
```

Example:

```json
[
  "DEMAND__TOTAL",
  "DEMAND__SERVEI_CODI__URG"
]
```

`models_columns_orders.txt` is the legacy/plain-text aggregation view of the
same modeled columns:

```text
DEMAND__TOTAL
DEMAND__SERVEI_CODI__URG
```

The JSON is canonical for current training scripts. The text file is kept for
inspection and compatibility with older handoffs.

## Diagnostic Covariates

Owner: `predap-cclr`

The training and inference modules consume CCLR outputs as diagnostic covariate
files. Private covariate files derived from real data must not be committed.

Expected private filename pattern:

```text
BEST_features_NOSMOOTH_<CODE>.xlsx
```

Training receives a prefix such as
`runtime/best_features/BEST_features_NOSMOOTH_` and appends the code plus
`.xlsx`.

## Model Bundle

Owner: `predap-training` or an external model provider.

Required:

- `manifest.json`
- real quantized weights under `<CODE>/<model_type>/`

The inference repository validates this structure before running predictions.
Public dummy bundles use JSON models. Real trained bundles must stay private and
should be validated with `--allow-real-data`.

Real private layout:

```text
private_runtime/quantized_models/
  manifest.json
  <CODE>/
    univariate_model/
    diagnostics_model/
    seasonal_model/
```

Supporting artifacts:

```text
private_runtime/models_parameters/
private_runtime/transformer_outputs/
private_runtime/history/
private_runtime/results/
```

`private_runtime/results` contains `performance_*.json` files used by
stage-aware inference to decide whether a horizon stops at `univariate`,
`diagnostics` or `seasonal`.

## Prediction Table

Owner: `predap-inference`

Inference writes three related outputs:

- a raw long Parquet dataset at `--output-path`;
- a selected long audit table at `<output-path>_selected_long.parquet`;
- a historical-like wide table at `<output-path>_wide.parquet` plus a CSV copy.

Required raw long columns:

- `code`
- `target_date`
- `init_forecast_date`
- `final_forecast_date`
- `prediction_origin_date`
- `horizon_day`
- `forecast`
- `lookback`
- `model_id`
- `predictions`
- `ci_lower`
- `ci_upper`
- `velocity`
- `acceleration`

The operational wide table contains:

- `prediction_origin_date`
- `timestamp`
- one main prediction column per target code;
- auxiliary columns named `<CODE>__ci_lower`, `<CODE>__ci_upper`,
  `<CODE>__forecast`, `<CODE>__lookback`, `<CODE>__horizon_day` and
  `<CODE>__model_id`;
- stage-audit columns named `<CODE>__model_stage_reached`,
  `<CODE>__selected_stage_wape`, `<CODE>__univariate_wape`,
  `<CODE>__diagnostics_wape` and `<CODE>__seasonal_wape`.

For a prediction origin X, rows start at X+1. The stitch rule chooses the
shortest trained horizon that covers each future day: 7, then 14, then 30,
then 60, then 182, then 365.

For each chosen horizon, inference stops at the best WAPE stage. If
`univariate` is best, no residual models are loaded; if `diagnostics` is best,
only the diagnostics residual correction is applied; if `seasonal` is best,
the full residual stack is applied.
