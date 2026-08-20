# Data Preparation

The data preparation layer converts historical daily datasets into model-ready
tables and sequences.

## Main Responsibilities

- Read CSV or Parquet historical datasets.
- Validate that `timestamp` exists.
- Keep one numeric column per target code.
- Add temporal features such as day-of-week, month and holiday indicators.
- Create lookback/forecast windows for training and inference.
- Keep the data contract consistent with `predap-data-retrieval`.

## Public Contract

The public synthetic workflow writes:

```text
runtime/synthetic_demo/retrieval_export/historical_daily.csv
runtime/synthetic_demo/retrieval_export/target_codes_models_columns_order.json
```

Real data follows the same schema but must remain outside GitHub.

## Relevant Source Areas

- `src/data_utils/`
- `src/config/base_transformer_config.py`
- `AQUAS_DATA_RETRIEVAL-git/docs/data_contract.md`

