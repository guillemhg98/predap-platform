# Docker Containers

Predap can be containerized for reproducible deployment across environments.

Docker is the preferred path for real training and production-style inference
because it avoids local Python/TensorFlow wheel mismatches. In particular,
Python 3.13 cannot install the currently supported local
`tensorflow-cpu<2.18,>=2.16` stack, while the Docker images provide a compatible
runtime from the NVIDIA TensorFlow base image.

---

## Dockerfile

The root `dockerfile` builds the training/API image from an NVIDIA TensorFlow
base image and installs `requirements.txt`. `PREDAP_INFERENCE/Dockerfile`
builds a smaller standalone inference image.

---

## Docker Compose

For the full training stack, use the project `docker-compose.yml`. It defines:

| Service | Purpose |
|---|---|
| `postgres` | MLflow backend store |
| `mlflow` | MLflow tracking server |
| `redis` | API job queue support |
| `api` | FastAPI application |
| `train-one` | Train and quantize one code |
| `train-sweep` | Hydra multirun training |
| `train-all` | Sequential batch training over all configured codes |

Default host ports in `.env.example` are `55001` for MLflow and `55433` for
PostgreSQL. If `.env` already exists, edit it directly; ignored local files are
not changed by `git pull`.

### Running

```bash
# Build and start
docker compose build
docker compose up -d postgres mlflow

# Train one code
docker compose --profile train run --rm train-one

# Train all configured codes
docker compose --profile all run --rm train-all

# Stop
docker compose down
```

---

## Training Container

For training jobs, configure private data paths in `.env`:

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

# Bundled in standalone predap-training. Change only for a custom CCLR checkout.
HOST_CCLR_REPO_DIR=./predap-cclr
CCLR_REPO_PATH=/app/predap-cclr
```

The Compose preflight and Hydra training command both receive these `TRAIN_*`
paths.

---

## GPU Configuration

| Runtime | Flag | Notes |
|---------|------|-------|
| Docker CLI | `--gpus all` | Requires NVIDIA Container Toolkit |
| Docker Compose | `gpus: all` | Used by the training services in `docker-compose.yml` |
| CPU-only | No GPU flags | TensorFlow falls back to CPU automatically |

!!! tip "NVIDIA Container Toolkit"
    Install the toolkit to enable GPU passthrough:
    ```bash
    sudo apt-get install -y nvidia-container-toolkit
    sudo systemctl restart docker
    ```

---

## Volume Mounts

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| Host setting | Container path | Purpose |
|---|---|---|
| `HOST_DATA_DIR` | `/app/private_runtime/data` | Private Parquet and target-code metadata |
| `HOST_BEST_FEATURES_DIR` | `/app/runtime/best_features` | CCLR `BEST_features_NOSMOOTH_<CODE>.xlsx` files |
| `HOST_QUANTIZED_MODELS_DIR` | `/quantized_models` | Quantized private model weights |
| `HOST_MODELS_PARAMETERS_DIR` | `/models_parameters` | Model metadata and parameters |
| `HOST_TRANSFORMER_OUTPUTS_DIR` | `/transformer_outputs` | Training artifacts |
| `HOST_HISTORY_DIR` | `/history` | Training history |
| `HOST_RESULTS_DIR` | `/app/runtime/results` | `performance_*.json` WAPE files used by stage-aware inference |
| `HOST_PRODUCTION_PREDICTIONS_DIR` | `/production_predictions` | Private prediction outputs |
| `HOST_CCLR_REPO_DIR` | `/app/predap-cclr` | Bundled `predap-cclr` folder, or an optional custom checkout, used to generate missing `BEST_features_NOSMOOTH_<CODE>.xlsx` files |
