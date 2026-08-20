# PREDAP Synthetic Workflow

This folder contains publishable dummy assets for testing the PREDAP platform
without exposing real healthcare data.

The synthetic workflow checks the same high-level contracts used by the real
platform:

1. data retrieval exports a historical daily dataset;
2. training creates a model bundle;
3. inference loads that bundle and writes prediction rows;
4. documentation and CI can validate the public example end to end.

Run the full smoke workflow:

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
```

Expected outputs:

```text
runtime/synthetic_demo/
  retrieval_export/
    historical_daily.csv
    training_until_YYYY-MM-DD.csv
    target_codes_models_columns_order.json
    models_columns_orders.txt
  model_bundle/
    manifest.json
    models/
  inference/
    predictions.csv
  metrics.json
```

The files under `fixtures/` are tiny static examples suitable for GitHub. The
generated files under `runtime/` are ignored by Git.

