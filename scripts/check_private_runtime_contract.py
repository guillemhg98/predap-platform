"""Validate that private runtime folders are ready for real PREDAP runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


REQUIRED_RUNTIME_DIRS = (
    "data",
    "best_features",
    "quantized_models",
    "models_parameters",
    "transformer_outputs",
    "history",
    "results",
    "production_predictions",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check private_runtime data, metadata and model artifact contracts."
    )
    parser.add_argument("--runtime-root", default="private_runtime")
    parser.add_argument("--require-models", action="store_true")
    parser.add_argument("--require-best-features", action="store_true")
    parser.add_argument("--require-selection-metrics", action="store_true")
    return parser.parse_args()


def load_codes(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing target-code metadata: {path}")
    codes = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(codes, list) or not codes or not all(isinstance(code, str) and code for code in codes):
        raise ValueError(f"{path} must contain a non-empty JSON list of target-code strings.")
    return codes


def check_timeseries(path: Path, codes: list[str], label: str) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")
    if path.suffix.lower() == ".parquet":
        schema = pq.read_schema(path)
        columns = schema.names
        timestamps = pd.read_parquet(path, columns=["timestamp"])["timestamp"]
    elif path.suffix.lower() == ".csv":
        header = pd.read_csv(path, nrows=0)
        columns = header.columns.tolist()
        timestamps = (
            pd.read_csv(path, usecols=["timestamp"])["timestamp"]
            if "timestamp" in columns
            else pd.Series([], dtype="datetime64[ns]")
        )
    else:
        raise ValueError(f"{label} must be .parquet or .csv: {path}")

    if "timestamp" not in columns:
        raise KeyError(f"{label} must contain a 'timestamp' column: {path}")

    missing_codes = [code for code in codes if code not in columns]
    if missing_codes:
        raise KeyError(
            f"{label} is missing {len(missing_codes)} code columns from target metadata. "
            f"First missing: {missing_codes[:10]}"
        )

    return {
        "path": str(path),
        "columns": len(columns),
        "codes_checked": len(codes),
        "min_timestamp": str(pd.to_datetime(timestamps).min()) if len(timestamps) else None,
        "max_timestamp": str(pd.to_datetime(timestamps).max()) if len(timestamps) else None,
    }


def check_plain_code_order(path: Path, codes: list[str]) -> dict[str, object]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    lines = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    missing = [code for code in codes if code not in lines]
    return {
        "path": str(path),
        "exists": True,
        "lines": len(lines),
        "missing_codes": missing[:10],
    }


def check_best_features(runtime_root: Path, codes: list[str], required: bool) -> dict[str, object]:
    root = runtime_root / "best_features"
    files = [root / f"BEST_features_NOSMOOTH_{code}.xlsx" for code in codes]
    missing = [path.name for path in files if not path.exists()]
    if required and missing:
        raise FileNotFoundError(f"Missing best-feature files. First missing: {missing[:10]}")
    return {"available": len(files) - len(missing), "expected": len(files), "missing_first": missing[:10]}


def check_model_bundle(runtime_root: Path, required: bool) -> dict[str, object]:
    model_root = runtime_root / "quantized_models"
    manifest = model_root / "manifest.json"
    if not manifest.exists():
        if required:
            raise FileNotFoundError(f"Missing quantized model manifest: {manifest}")
        return {"manifest": str(manifest), "exists": False}

    payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
    model_counts = {}
    for code in payload.get("target_codes", []):
        code_dir = model_root / str(code)
        model_counts[str(code)] = len(list(code_dir.rglob("*.h5"))) if code_dir.exists() else 0
    return {
        "manifest": str(manifest),
        "exists": True,
        "target_codes": payload.get("target_codes", []),
        "forecasts": payload.get("forecasts", []),
        "lookbacks": payload.get("lookbacks", []),
        "model_counts": model_counts,
    }


def check_selection_metrics(runtime_root: Path, required: bool) -> dict[str, object]:
    root = runtime_root / "results"
    files = list(root.rglob("performance_*.json")) if root.exists() else []
    if required and not files:
        raise FileNotFoundError(f"No performance_*.json files found under {root}")
    return {"root": str(root), "performance_json_files": len(files)}


def main() -> int:
    args = parse_args()
    runtime_root = Path(args.runtime_root)
    if not runtime_root.exists():
        raise FileNotFoundError(f"Missing private runtime root: {runtime_root}")

    missing_dirs = [name for name in REQUIRED_RUNTIME_DIRS if not (runtime_root / name).exists()]
    if missing_dirs:
        raise FileNotFoundError(f"Missing private runtime directories: {missing_dirs}")

    data_root = runtime_root / "data"
    codes = load_codes(data_root / "target_codes_models_columns_order.json")
    summary = {
        "runtime_root": str(runtime_root),
        "target_codes": len(codes),
        "training_timeseries": check_timeseries(data_root / "historical_daily.parquet", codes, "training historical Parquet"),
        "inference_timeseries": check_timeseries(data_root / "inference_daily.parquet", codes, "inference Parquet"),
        "diagnostics_csv": check_timeseries(data_root / "historical_daily.csv", codes, "diagnostics historical CSV"),
        "models_columns_orders": check_plain_code_order(data_root / "models_columns_orders.txt", codes),
        "best_features": check_best_features(runtime_root, codes, args.require_best_features),
        "model_bundle": check_model_bundle(runtime_root, args.require_models),
        "stage_selection_metrics": check_selection_metrics(runtime_root, args.require_selection_metrics),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
