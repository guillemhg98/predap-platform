"""Log inference output files to MLflow as run artifacts."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Log PREDAP inference outputs to MLflow.")
    parser.add_argument(
        "--tracking-uri",
        default=os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"),
        help="MLflow tracking URI.",
    )
    parser.add_argument(
        "--experiment-name",
        default=os.getenv("INFERENCE_EXPERIMENT_NAME", "PREDAP_Inference_Outputs"),
        help="MLflow experiment name.",
    )
    parser.add_argument(
        "--run-name",
        default=os.getenv("INFERENCE_RUN_NAME"),
        help="Optional MLflow run name.",
    )
    parser.add_argument(
        "--predictions-root",
        default=os.getenv("INFERENCE_OUTPUT_ROOT", "/production_predictions"),
        help="Folder that contains inference output files.",
    )
    parser.add_argument(
        "--output-prefix",
        default=os.getenv("INFERENCE_OUTPUT_PREFIX", "real/final_output_predictions"),
        help="Output prefix used by the inference CLI.",
    )
    parser.add_argument(
        "--prediction-origin-date",
        default=os.getenv("INFERENCE_PREDICTION_ORIGIN_DATE"),
        help="Optional prediction origin date to store as a run parameter.",
    )
    parser.add_argument(
        "--batch-label",
        default=os.getenv("INFERENCE_BATCH_LABEL"),
        help="Optional batch label to group related inference runs.",
    )
    parser.add_argument(
        "--metrics-path",
        default=os.getenv("INFERENCE_METRICS_PATH"),
        help="Optional metrics file to log if present.",
    )
    return parser


def existing_paths(root: Path, prefix: str, metrics_path: str | None) -> dict[str, Path]:
    candidates = {
        "raw_long": root / prefix,
        "selected_long": root / f"{prefix}_selected_long.parquet",
        "wide_parquet": root / f"{prefix}_wide.parquet",
        "wide_csv": root / f"{prefix}_wide.csv",
    }
    if metrics_path:
        candidates["metrics"] = Path(metrics_path)
    return {name: path for name, path in candidates.items() if path.exists()}


def infer_row_metrics(paths: dict[str, Path]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    selected_path = paths.get("selected_long")
    wide_path = paths.get("wide_parquet")

    if selected_path:
        selected_df = pd.read_parquet(selected_path)
        metrics["selected_rows"] = float(len(selected_df))
        if "horizon_day" in selected_df.columns and not selected_df.empty:
            metrics["max_horizon_day"] = float(selected_df["horizon_day"].max())
        if "code" in selected_df.columns:
            metrics["target_codes"] = float(selected_df["code"].nunique())
        if "model_stage_reached" in selected_df.columns:
            for stage, count in selected_df["model_stage_reached"].value_counts().items():
                safe_stage = str(stage).replace(" ", "_").replace("-", "_")
                metrics[f"stage_rows_{safe_stage}"] = float(count)

    if wide_path:
        wide_df = pd.read_parquet(wide_path)
        metrics["wide_rows"] = float(len(wide_df))
        metrics["wide_columns"] = float(len(wide_df.columns))

    raw_path = paths.get("raw_long")
    if raw_path and raw_path.is_dir():
        metrics["raw_parquet_files"] = float(len(list(raw_path.rglob("*.parquet"))))

    return metrics


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.predictions_root)
    paths = existing_paths(root, args.output_prefix, args.metrics_path)
    if not paths:
        raise FileNotFoundError(
            f"No inference outputs found under {root} with prefix {args.output_prefix}."
        )

    import mlflow

    mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment(args.experiment_name)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_prefix = args.output_prefix.replace("\\", "_").replace("/", "_")
    run_name = args.run_name or f"inference_{safe_prefix}_{timestamp}"
    with mlflow.start_run(run_name=run_name):
        active_run = mlflow.active_run()
        mlflow.log_params(
            {
                "output_prefix": args.output_prefix,
                "predictions_root": str(root),
                "run_kind": "daily_inference" if args.prediction_origin_date else "inference",
            }
        )
        if args.prediction_origin_date:
            mlflow.log_param("prediction_origin_date", args.prediction_origin_date)
        if args.batch_label:
            mlflow.log_param("batch_label", args.batch_label)

        metrics = infer_row_metrics(paths)
        if metrics:
            mlflow.log_metrics(metrics)

        for artifact_name, path in paths.items():
            if path.is_dir():
                mlflow.log_artifacts(str(path), artifact_path=artifact_name)
            else:
                mlflow.log_artifact(str(path), artifact_path=artifact_name)

    print(f"Logged inference outputs to MLflow experiment: {args.experiment_name}")
    print(f"Run name: {run_name}")
    if active_run is not None:
        print(f"Run ID: {active_run.info.run_id}")
    for artifact_name, path in paths.items():
        print(f"- {artifact_name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
