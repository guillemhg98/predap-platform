# PREDAP Platform

PREDAP is a modular platform for healthcare demand forecasting. The project is
organized so each capability can live in its own GitHub repository while still
working together through documented data, model and prediction contracts.

## Project Objectives

PREDAP is designed to:

- standardize real retrieval outputs into daily time-series contracts;
- select diagnostic covariates with CCLR;
- train and quantize Transformer forecasting models;
- track real training and recovered artifacts in MLflow;
- validate model bundles before inference;
- keep public GitHub repositories free of real data and private model artifacts.

## Public Data Rule

No real healthcare data can be published to GitHub.

Public repositories may contain:

- source code;
- documentation;
- CI workflows;
- synthetic dummy data;
- dummy model bundles created only for smoke tests and tutorials.

Public repositories must not contain:

- real CSV, Excel, Parquet or database exports;
- model weights trained on real data;
- MLflow runs or artifacts;
- production predictions;
- `.env` files, credentials or connection strings.

## Modules

| GitHub repository | Local source | Purpose |
|---|---|---|
| `predap-platform` | `.` | Orchestration, Docker Compose, documentation and GitHub Pages. |
| `predap-data-retrieval` | `AQUAS_DATA_RETRIEVAL-git/` | Data connectors, schema validation and retrieval exports. |
| `predap-cclr` | `CCLR_PREDAP/` | CCLR feature selection and diagnostic covariate generation. |
| `predap-training` | `src/`, `conf/`, `main_train*.py`, `scripts/` | Transformer training, quantization and MLflow tracking. |
| `predap-inference` | `PREDAP_INFERENCE/` | External model validation, reconstruction and prediction exports. |
| `prediction-analysis` | `prediction-analysis/` | Prediction-vs-observed evaluation tables, plots and MLflow logging. |

The file [PREDAP_PLATFORM.yml](PREDAP_PLATFORM.yml) is the machine-readable
manifest for these boundaries.

## Synthetic End-to-End Smoke Test

Run the public dummy workflow from the platform root:

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
```

This creates:

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

The workflow proves that a user can retrieve dummy data, train a dummy model
bundle and run dummy inference without any private dataset.

## Python and Docker Compatibility

Use Python 3.10, 3.11 or 3.12 for environments that install TensorFlow. Do not
use Python 3.13 for real training or full inference dependency installs. For a
local training virtualenv, install `requirements-training-local.txt`; it includes
`requirements.txt` plus `tensorflow-cpu<2.18,>=2.16`, and that TensorFlow range
does not publish Python 3.13 wheels.

If the Windows `py` launcher is unavailable, call the Python executable
directly:

```powershell
C:\Users\Guillem\AppData\Local\Programs\Python\Python310\python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-training-local.txt
```

The public toy workflow and docs build can run with a newer Python if their
dependencies are already installed, because they do not import TensorFlow. For
real training, quantization and production-style inference, prefer Docker or a
Python 3.10-3.12 virtual environment.

For the exact mapping from toy artifacts to real private subprocesses, see
`docs/platform/toy-vs-real-map.md`.

Start with the full copy-paste guide:

```text
docs/tutorials/practical-runbook.md
```

For a copy-paste walkthrough from a GitHub clone through toy validation,
real-data training with MLflow and publishing the split repositories, see
`docs/tutorials/github-to-production-check.md`.

For the real private path starting from data-retrieval `finals/` outputs and
ending in production predictions, see
`docs/tutorials/real-retrieval-to-prediction.md`.

## Training Stack

Start the production support services:

```powershell
Copy-Item .env.example .env
docker compose build
docker compose up -d postgres mlflow
```

By default `.env.example` uses host port `55001` for MLflow and `55433` for
PostgreSQL to avoid common local conflicts. MLflow is exposed on the host port
configured in `.env`:

```powershell
$MlflowPort = ((Select-String -Path .env -Pattern '^MLFLOW_HOST_PORT=').Line -split '=', 2)[1]
$MlflowUrl = "http://127.0.0.1:$MlflowPort"
Start-Process $MlflowUrl
```

Train one configured target code:

```powershell
$env:TRAIN_TARGET_CODE="DEMAND__TOTAL"
$env:TRAIN_EXPERIMENT_SETUP="7_7"
docker compose --profile train run --rm train-one
```

Run all configured codes and horizons:

```powershell
docker compose --profile all run --rm train-all
```

Training expects private data mounted locally under ignored runtime paths. For
a fresh GitHub clone, create `private_runtime/` and put real artifacts here:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\create_private_runtime_skeleton.ps1 -Profile platform
```

```text
private_runtime/data/historical_daily.parquet
private_runtime/data/inference_daily.parquet
private_runtime/data/historical_daily.csv
private_runtime/data/target_codes_models_columns_order.json
private_runtime/best_features/BEST_features_NOSMOOTH_<CODE>.xlsx
private_runtime/quantized_models/
private_runtime/results/
private_runtime/production_predictions/
```

Set `TRAIN_DATA_PATH`, `TRAIN_ALL_CODES_PATH` and
`TRAIN_BEST_FEATURES_PREFIX` in `.env` so the preflight checks and training
entrypoint read the same private artifacts. Do not commit those files. The full
placement contract is in `docs/platform/private-runtime-setup.md`.

If `BEST_features_NOSMOOTH_<CODE>.xlsx` is missing, training can generate it
through CCLR when CCLR is available. The training dependencies include the CCLR
Python stack needed for this auto-generation. In split repositories, clone
`predap-cclr` next to `predap-training` or set `CCLR_REPO_PATH` to that folder.
For Docker, set `HOST_CCLR_REPO_DIR` to the host folder that contains
`predap-cclr`; Compose mounts it at `/app/predap-cclr`. The default value points
to `private_runtime/cclr_repo`, an ignored placeholder that keeps Docker happy
when the Excel feature files already exist. Use
`scripts\check_private_runtime_contract.py --require-best-features` only when
you want to require all CCLR Excel files to exist before training starts.

### Standalone Training Guarantees

The standalone `predap-training` repository is prepared so it can be cloned and
run without importing source files from another repository. It includes the
training code, quantization helper used by `main_train_quantization.py`,
Docker/MLflow configuration, CCLR import helper and local dependency file.

These standalone changes do not change model science defaults: epochs, learning
rate, architecture, horizons, batch-size logic and Hydra hyperparameters still
come from `conf/config_production_quantization.yaml`, `conf/config_production.yaml`
and explicit command-line overrides.

On Windows, local subprocesses are launched with UTF-8 output settings by
`scripts/train_all_codes.py`, and training log messages avoid non-ASCII symbols.
This prevents `UnicodeEncodeError` failures in PowerShell consoles using
`cp1252`.

## Inference With External Models

Validate an uploaded model bundle before inference:

```powershell
python PREDAP_INFERENCE/production/validate_model_bundle.py --model-folder runtime/synthetic_demo/model_bundle
```

When using independent GitHub repositories, run the validator from the
`predap-inference` clone and point it at the platform output folder.

For production, mount the real historical dataset and private model bundle into
the inference container. The model bundle contract is documented in
`PREDAP_INFERENCE/docs/model_bundle_contract.md`.

## Documentation and GitHub Pages

Install documentation dependencies:

```powershell
pip install -r docs-requirements.txt
```

Serve locally:

```powershell
mkdocs serve
```

Build strictly:

```powershell
mkdocs build --strict
```

GitHub Pages is configured through `.github/workflows/docs.yml`.

## Preparing Independent GitHub Repositories

The intended split is:

```text
predap-platform
predap-data-retrieval
predap-cclr
predap-training
predap-inference
prediction-analysis
```

Use the export helper to stage clean publishable copies:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\export_independent_repos.ps1 -OutputRoot dist\github-repos -Force -RunSafetyCheck
```

Preview Git initialization, commits and remotes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 -ReposRoot dist\github-repos -RemoteBaseUrl https://github.com/<org> -DryRun
```

Replace `<org>` with your GitHub username or organization. If GitHub CLI
`gh` is not installed, create the empty repositories manually in the GitHub web
UI before running the final push.

Publish only after confirming the final GitHub organization and repository
names:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 -ReposRoot dist\github-repos -RemoteBaseUrl https://github.com/<org> -Push
```

If you already pushed an initial broken export to brand-new repositories, add
`-ForcePush` to replace it with `git push --force-with-lease`.
If any remote was created with an initial README/LICENSE or contains an older
export, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 -ReposRoot dist\github-repos -RemoteBaseUrl https://github.com/<org> -Push -ForceRemote -ForcePush
```

The full publishing and submodule tutorial is documented in
`docs/tutorials/full-platform-workflow.md`.
The end-to-end GitHub checklist is documented in
`docs/tutorials/github-to-production-check.md`.

## Direct Push Commands

After exporting clean standalone repositories and creating empty GitHub repos,
push each export from `dist/github-repos`:

```powershell
Set-Location dist\github-repos\predap-platform
git init
git branch -M main
git remote add origin https://github.com/<org>/predap-platform.git
git add .
git commit -m "Prepare standalone PREDAP platform"
git push -u origin main

Set-Location ..\predap-data-retrieval
git init
git branch -M main
git remote add origin https://github.com/<org>/predap-data-retrieval.git
git add .
git commit -m "Prepare standalone data retrieval module"
git push -u origin main

Set-Location ..\predap-cclr
git init
git branch -M main
git remote add origin https://github.com/<org>/predap-cclr.git
git add .
git commit -m "Prepare standalone CCLR module"
git push -u origin main

Set-Location ..\predap-training
git init
git branch -M main
git remote add origin https://github.com/<org>/predap-training.git
git add .
git commit -m "Prepare standalone training module"
git push -u origin main

Set-Location ..\predap-inference
git init
git branch -M main
git remote add origin https://github.com/<org>/predap-inference.git
git add .
git commit -m "Prepare standalone inference module"
git push -u origin main

Set-Location ..\prediction-analysis
git init
git branch -M main
git remote add origin https://github.com/<org>/prediction-analysis.git
git add .
git commit -m "Prepare standalone prediction analysis module"
git push -u origin main
```

## Contact, License and Use

- Support and contact routes: `SUPPORT.md` and
  `docs/platform/contact-support.md`.
- Security and data exposure: `SECURITY.md`.
- Data publication rules: `DATA_POLICY.md`.
- License and permitted use: Apache 2.0 in `LICENSE`, summarized in
  `docs/platform/license-and-use.md`.
