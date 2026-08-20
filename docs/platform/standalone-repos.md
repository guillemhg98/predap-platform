# Standalone Repositories

Each PREDAP repository must work after a fresh GitHub clone without reading
files from another local repository. Cross-repo handoffs happen through copied
or mounted artifacts, not relative imports into a sibling checkout.

## Common Private Layout

Every standalone repo may create an ignored `private_runtime/` folder at its
own root. GitHub should contain code, docs and synthetic fixtures only.

```text
private_runtime/
  data/
  best_features/
  quantized_models/
  models_parameters/
  transformer_outputs/
  history/
  results/
  production_predictions/
  analysis/
```

Use only the subfolders a repo needs. For example, `predap-data-retrieval`
usually writes `private_runtime/data/`, while `prediction-analysis` reads
`private_runtime/production_predictions/` and writes `private_runtime/analysis/`.

## Repo Responsibilities

| Repo | Put real inputs here | Writes real outputs here |
|---|---|---|
| `predap-data-retrieval` | private source exports, credentials outside Git | `private_runtime/data/` |
| `predap-cclr` | `private_runtime/data/historical_daily.parquet` or `.csv` | `private_runtime/best_features/` |
| `predap-training` | `private_runtime/data/`, `private_runtime/best_features/` | `private_runtime/quantized_models/`, `private_runtime/results/`, MLflow artifacts |
| `predap-inference` | `private_runtime/data/`, `private_runtime/quantized_models/`, `private_runtime/best_features/`, `private_runtime/results/` | `private_runtime/production_predictions/` |
| `prediction-analysis` | `private_runtime/production_predictions/`, `private_runtime/data/inference_daily.parquet` | `private_runtime/analysis/` |

## Clone Checklist

```powershell
git clone https://github.com/<org>/<repo>.git
Set-Location <repo>
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\create_private_runtime_skeleton.ps1 -Profile <profile>
```

Use one of these profiles: `data-retrieval`, `cclr`, `training`, `inference`,
`analysis` or `platform`. Then copy private artifacts into the created folders.
Never commit `private_runtime/`, `runtime/`, `outputs/`, `.env`, real tables,
model weights, MLflow folders or production predictions.

## Validation

From the platform or training repo, validate a real runtime:

```powershell
python scripts\check_private_runtime_contract.py --runtime-root private_runtime
```

From the inference repo, validate a model bundle:

```powershell
python production\validate_model_bundle.py --model-folder private_runtime\quantized_models --allow-real-data
```

From the analysis repo, run a small analysis after predictions and observed
actuals exist:

```powershell
python -m prediction_analysis analyze `
  --predictions-root private_runtime\production_predictions\real `
  --actuals private_runtime\data\inference_daily.parquet `
  --output-dir private_runtime\analysis\latest
```
