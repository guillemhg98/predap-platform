# Installation

## Requirements

For the public synthetic workflow:

- Python 3.10 or newer. The toy workflow does not import TensorFlow.

For real training and inference:

- Docker Desktop or a compatible Docker engine;
- Python 3.10, 3.11 or 3.12 when installing TensorFlow locally;
- TensorFlow-compatible GPU stack for heavy training;
- private data mounted outside Git;
- private model/artifact storage.

Do not use Python 3.13 for local real training/inference installs while the
local training install uses `tensorflow-cpu<2.18,>=2.16`. That TensorFlow range
has no Python 3.13 wheel, so `pip install -r requirements-training-local.txt`
can fail with:

```text
ERROR: No matching distribution found for tensorflow-cpu<2.18,>=2.16
```

Use Docker or create the virtual environment with an installed Python 3.10-3.12
executable:

```powershell
C:\Users\Guillem\AppData\Local\Programs\Python\Python310\python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If the `py` launcher is installed, this equivalent command is fine:

```powershell
py -3.12 -m venv .venv
```

## Clone

```bash
git clone https://github.com/<org>/predap-platform.git
cd predap-platform
```

If using submodules after the repos are split:

```bash
git submodule update --init --recursive
```

## Public Smoke Test

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
python PREDAP_INFERENCE/production/validate_model_bundle.py --model-folder runtime/synthetic_demo/model_bundle
```

This path does not need TensorFlow, pandas or private data.

## Documentation

```powershell
pip install -r docs-requirements.txt
mkdocs serve
```

## Runtime Configuration

Create a local environment file from the safe template:

```powershell
Copy-Item .env.example .env
```

Edit `.env` for local paths and ports. Never commit `.env`.

For real data, first create and populate the ignored private folders described
in [Private Runtime Setup](../platform/private-runtime-setup.md). That page
defines which retrieval, CCLR, model, WAPE and prediction artifacts must be
downloaded or generated and where each one belongs.

## Production Dependencies

Install the full Python stack only for private training/inference environments:

```powershell
pip install -r requirements-training-local.txt
```

Main dependency groups:

| Package | Purpose |
|---|---|
| TensorFlow/Keras | Transformer models and quantization |
| pandas, numpy, pyarrow | Data processing |
| scikit-learn, scipy, statsmodels | Metrics, preprocessing and statistical models |
| MLflow | Experiment tracking |
| Hydra/OmegaConf | Configuration and sweeps |
| FastAPI/Uvicorn | API layer |
| PostgreSQL/Redis clients | Production services |

## Docker Services

```powershell
docker compose build
docker compose up -d postgres mlflow
```

Optional API profile:

```powershell
docker compose --profile api up -d api
```

Training profiles:

```powershell
docker compose --profile train run --rm train-one
docker compose --profile all run --rm train-all
```
