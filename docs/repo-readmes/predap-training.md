# PREDAP Training

Independent training and quantization repository for the PREDAP platform.

This repo owns Transformer training, residual correction training, model
quantization and MLflow experiment tracking. It consumes historical datasets
from `predap-data-retrieval` and uses the bundled `predap-cclr/` folder for
diagnostic covariate generation, then exports private model bundles consumed by
`predap-inference`.

## Public Data Policy

Do not commit real healthcare data, model weights trained on real data, MLflow
runs, local outputs or `.env` files. Public tutorials must use synthetic data
and dummy models only.

## Main Entrypoints

```bash
python main_train.py
python main_train_quantization.py
python scripts/train_all_codes.py
```

## Python and Docker Compatibility

For local installs, use Python 3.10, 3.11 or 3.12. Do not use Python 3.13 for
real training. Local virtualenvs should install
`requirements-training-local.txt`, which includes `requirements.txt` plus
`tensorflow-cpu<2.18,>=2.16`; pip will not find that TensorFlow wheel on Python
3.13. Docker is the recommended path for real training because it provides the
expected TensorFlow runtime.

On Windows, if the `py` launcher is missing, create the virtual environment with
the full Python path:

```powershell
C:\Users\Guillem\AppData\Local\Programs\Python\Python310\python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-training-local.txt
```

## Standalone Real-Data Placement

After cloning this repository from GitHub, create the ignored private folders:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\create_private_runtime_skeleton.ps1 -Profile training
```

Put real retrieval and CCLR artifacts here:

```text
private_runtime/data/historical_daily.parquet
private_runtime/data/inference_daily.parquet
private_runtime/data/historical_daily.csv
private_runtime/data/target_codes_models_columns_order.json
private_runtime/data/models_columns_orders.txt
private_runtime/best_features/BEST_features_NOSMOOTH_<CODE>.xlsx
```

Training writes private artifacts here:

```text
private_runtime/quantized_models/
private_runtime/models_parameters/
private_runtime/transformer_outputs/
private_runtime/history/
private_runtime/results/
private_runtime/production_predictions/
runtime/mlflow/
```

Copy `.env.example` to `.env` and keep these paths aligned:

```text
HOST_DATA_DIR=./private_runtime/data
HOST_BEST_FEATURES_DIR=./private_runtime/best_features
HOST_QUANTIZED_MODELS_DIR=./private_runtime/quantized_models
HOST_MODELS_PARAMETERS_DIR=./private_runtime/models_parameters
HOST_TRANSFORMER_OUTPUTS_DIR=./private_runtime/transformer_outputs
HOST_HISTORY_DIR=./private_runtime/history
HOST_RESULTS_DIR=./private_runtime/results

TRAIN_DATA_PATH=private_runtime/data/historical_daily.parquet
TRAIN_ALL_CODES_PATH=private_runtime/data/target_codes_models_columns_order.json
TRAIN_BEST_FEATURES_PREFIX=runtime/best_features/BEST_features_NOSMOOTH_
```

Run the contract check before real training:

```powershell
python scripts\check_private_runtime_contract.py --runtime-root private_runtime
```

Use `--require-best-features` only when you expect every
`BEST_features_NOSMOOTH_<CODE>.xlsx` file to be precomputed. If a target-code
Excel is missing, the training entrypoint can generate it through CCLR, but only
when CCLR is importable. The standalone GitHub package includes CCLR under
`predap-cclr/`, so a clean clone does not need a second repository. The training
requirements already include the CCLR runtime dependencies such as `seaborn`,
`statsmodels`, `scipy` and `IPython`.

For local Python runs, the bundled path is:

```powershell
$env:CCLR_REPO_PATH="D:\PREDAP_GITHUB_CLEAN_CHECK\predap-training\predap-cclr"
```

For Docker, `.env.example` already uses the bundled path:

```text
HOST_CCLR_REPO_DIR=./predap-cclr
CCLR_REPO_PATH=/app/predap-cclr
```

Only change those values if you intentionally want to test another local CCLR
checkout.

Preflight for one code reports whether the CCLR import is available and whether
the best-feature file already exists or will be generated:

```powershell
python scripts\preflight_training.py `
  --data-path private_runtime\data\historical_daily.parquet `
  --codes-path private_runtime\data\target_codes_models_columns_order.json `
  --target-code DEMAND__TOTAL `
  --best-features-prefix private_runtime\best_features\BEST_features_NOSMOOTH_
```

## Docker Workflow

Start support services:

```powershell
Copy-Item .env.example .env
docker compose build
docker compose up -d postgres mlflow
```

Default ports in `.env.example` are:

```text
POSTGRES_HOST_PORT=55433
MLFLOW_HOST_PORT=55001
```

If your local `.env` already exists, Git will not overwrite it. Edit those two
values manually when another service is already using the old ports.

Open MLflow:

```powershell
$MlflowPort = ((Select-String -Path .env -Pattern '^MLFLOW_HOST_PORT=').Line -split '=', 2)[1]
$MlflowUrl = "http://127.0.0.1:$MlflowPort"
Start-Process $MlflowUrl
```

Train one target:

```powershell
$env:TRAIN_TARGET_CODE="DEMAND__TOTAL"
$env:TRAIN_EXPERIMENT_SETUP="7_7"
docker compose --profile train run --rm train-one
```

Train all configured codes:

```powershell
docker compose --profile all run --rm train-all
```

Import copied/recovered private model artifacts into MLflow:

```powershell
$env:IMPORT_MODEL_CODE="DEMAND__TOTAL"
$env:IMPORT_SOURCE_LABEL="recovered_from_predap_production_simplified"
docker compose --profile mlflow-import run --rm mlflow-import
```

Then open the `PREDAP_Recovered_Artifacts` experiment in the MLflow UI.

Train the long `DEMAND__TOTAL` horizons:

```powershell
$env:TRAIN_TARGET_CODE="DEMAND__TOTAL"
$env:TRAIN_EXPERIMENT_SETUP="182_182"
docker compose --profile train run --rm train-one
$env:TRAIN_EXPERIMENT_SETUP="365_182"
docker compose --profile train run --rm train-one
```

## Standalone Behavior and Training Defaults

This repository is standalone after a GitHub clone. It includes:

- the Transformer training code in `src/`;
- the quantization helper required by `main_train_quantization.py`;
- `scripts/train_all_codes.py` for sequential batch training;
- `src/utils/cclr_import.py` to locate bundled `predap-cclr/`, a sibling
  `predap-cclr` clone or `CCLR_REPO_PATH`;
- `requirements-training-local.txt` for local virtualenv installs with
  TensorFlow.

These packaging changes do not modify the training recipe. Epochs, learning
rate, model architecture, horizons, batch-size logic and other hyperparameters
still come from the Hydra config files under `conf/` and from explicit command
overrides such as `experiment_setup="'7_7'"`.

On Windows, `scripts/train_all_codes.py` forces UTF-8 for child Python
processes. Training messages are ASCII-only so PowerShell consoles using
`cp1252` do not fail with `UnicodeEncodeError`.

## Synthetic Smoke Test

The platform-level synthetic workflow creates dummy data, dummy models and
dummy predictions without importing the heavy training stack:

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
```

Use that workflow in CI to check public contracts. Use the real training
entrypoints only in private environments where the data and GPU dependencies
are available.

Real training reads `TRAIN_DATA_PATH`, `TRAIN_ALL_CODES_PATH` and
`TRAIN_BEST_FEATURES_PREFIX` from `.env`; those values are passed to both the
preflight check and Hydra training config.

## Outputs

Private training outputs belong in ignored runtime paths:

- `private_runtime/quantized_models/`
- `private_runtime/models_parameters/`
- `private_runtime/transformer_outputs/`
- `private_runtime/history/`
- `private_runtime/results/`
- `private_runtime/production_predictions/`
- `runtime/mlflow/`

Publish metadata and documentation, not private artifacts.
