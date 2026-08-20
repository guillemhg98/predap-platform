# Testing

PREDAP has two levels of validation: public contract smoke tests and private
training/inference tests.

## Public Smoke Test

This test is safe for GitHub CI because it uses only synthetic data and dummy
models:

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
python PREDAP_INFERENCE/production/validate_model_bundle.py --model-folder runtime/synthetic_demo/model_bundle
python scripts/validate_synthetic_outputs.py --output-dir runtime/synthetic_demo
python -m py_compile `
  examples/synthetic/predap_synthetic_workflow.py `
  scripts/validate_synthetic_outputs.py `
  scripts/check_private_runtime_contract.py `
  PREDAP_INFERENCE/production/validate_model_bundle.py `
  PREDAP_INFERENCE/production/model_stage_selection.py `
  PREDAP_INFERENCE/production/output_formatting.py
```

The GitHub Actions workflow `.github/workflows/ci.yml` runs these checks.

## GitHub Safety Check

Before publishing exported repositories:

```powershell
.\scripts\check_github_safety.ps1 -Path dist\github-repos
```

The check fails on real-data-like artifacts such as Parquet, Excel, trained
model files, MLflow folders and CSV files outside `examples/synthetic/`.

## Private Tests

Private environments can run heavier tests with real mounted data:

```powershell
python scripts\check_private_runtime_contract.py --runtime-root private_runtime
python scripts\check_private_runtime_contract.py `
  --runtime-root private_runtime `
  --require-best-features `
  --require-models `
  --require-selection-metrics
python PREDAP_INFERENCE\production\validate_model_bundle.py `
  --model-folder private_runtime\quantized_models `
  --allow-real-data
```

Recommended private test areas:

- data retrieval schema checks;
- CCLR covariate generation on approved private fixtures;
- Transformer training on a reduced private cohort;
- quantization and model-bundle export;
- stage-aware inference over a private validation period;
- MLflow logging of recovered models and inference outputs;
- API contract tests.
