"""Run one inference job per prediction origin date and log each day to MLflow."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from math import ceil
from pathlib import Path

import pandas as pd


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def first_existing_path(*candidates: str) -> str:
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return candidates[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run PREDAP inference for consecutive daily prediction origins. "
            "Each origin writes separated files and becomes one MLflow run."
        )
    )
    parser.add_argument("--input-directory", default=env("DAILY_INFERENCE_INPUT_PATH", "/app/private_runtime/data/inference_daily.parquet"))
    parser.add_argument("--old-input-directory", default=env("DAILY_INFERENCE_OLD_INPUT_PATH", "/app/private_runtime/data/historical_daily.csv"))
    parser.add_argument("--model-folder", default=env("DAILY_INFERENCE_MODEL_FOLDER", "/quantized_models"))
    parser.add_argument("--predictions-root", default=env("DAILY_INFERENCE_PREDICTIONS_ROOT", "/production_predictions"))
    parser.add_argument("--output-subdir", default=env("DAILY_INFERENCE_OUTPUT_SUBDIR", "real/daily"))
    parser.add_argument(
        "--metrics-df-path",
        default=env("DAILY_INFERENCE_METRICS_DF_PATH", "/production_predictions/real/daily/production_evaluation_metrics.parquet"),
    )
    parser.add_argument(
        "--diagnostic-covariates-path",
        default=env("DAILY_INFERENCE_DIAGNOSTIC_COVARIATES_PATH", "/app/runtime/best_features/BEST_features_NOSMOOTH_"),
    )
    parser.add_argument(
        "--model-selection-metrics-dir",
        default=env("DAILY_INFERENCE_MODEL_SELECTION_METRICS_DIR", env("INFERENCE_MODEL_SELECTION_METRICS_DIR", "/app/runtime/results")),
    )
    parser.add_argument("--lookback-list", default=env("DAILY_INFERENCE_LOOKBACK_LIST", "7,14,60,60,182,182"))
    parser.add_argument("--forecast-list", default=env("DAILY_INFERENCE_FORECAST_LIST", "7,14,30,60,182,365"))
    parser.add_argument(
        "--code",
        action="append",
        dest="repeated_codes",
        help="Target code to run. Repeat to run multiple codes. Defaults to DAILY_INFERENCE_CODES or discovered codes.",
    )
    parser.add_argument(
        "--codes",
        dest="csv_codes",
        default=env("DAILY_INFERENCE_CODES"),
        help="Comma-separated target codes. Used together with repeated --code values.",
    )
    parser.add_argument(
        "--codes-file",
        default=env("DAILY_INFERENCE_CODES_FILE"),
        help=(
            "Optional JSON/CSV/TXT file with target codes. When omitted and no "
            "--code/--codes values are provided, codes are discovered from the "
            "input dataset and intersected with model folders when possible."
        ),
    )
    parser.add_argument("--start-date", default=env("DAILY_INFERENCE_START_DATE"))
    parser.add_argument("--end-date", default=env("DAILY_INFERENCE_END_DATE"))
    parser.add_argument("--days", type=int, default=int(env("DAILY_INFERENCE_DAYS", "7") or "7"))
    parser.add_argument("--workers", type=int, default=int(env("DAILY_INFERENCE_WORKERS", "1") or "1"), help="Number of parallel code shards per prediction origin.")
    parser.add_argument("--codes-per-worker", type=int, default=int(env("DAILY_INFERENCE_CODES_PER_WORKER", "0") or "0"), help="Optional fixed number of codes per shard. Defaults to an even split across --workers.")
    parser.add_argument("--keep-shards", action=argparse.BooleanOptionalAction, default=env_flag("DAILY_INFERENCE_KEEP_SHARDS"), help="Keep temporary per-shard outputs after the merged daily files are written.")
    parser.add_argument("--tf-intra-op-threads", default=env("DAILY_INFERENCE_TF_INTRA_OP_THREADS"), help="Optional TF_NUM_INTRAOP_THREADS value for inference workers.")
    parser.add_argument("--tf-inter-op-threads", default=env("DAILY_INFERENCE_TF_INTER_OP_THREADS"), help="Optional TF_NUM_INTEROP_THREADS value for inference workers.")
    parser.add_argument("--tracking-uri", default=env("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    parser.add_argument("--experiment-name", default=env("DAILY_INFERENCE_EXPERIMENT_NAME", env("INFERENCE_EXPERIMENT_NAME", "PREDAP_Inference_Outputs")))
    parser.add_argument("--batch-label", default=env("DAILY_INFERENCE_BATCH_LABEL"))
    parser.add_argument("--skip-mlflow", action="store_true", help="Write daily outputs but do not log runs to MLflow.")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue with later days after a failed day.")
    parser.add_argument(
        "--inference-script",
        default=env(
            "DAILY_INFERENCE_SCRIPT",
            first_existing_path(
                "PREDAP_INFERENCE/production/retrieve_and_reconstruct_data_pipeline.py",
                "production/retrieve_and_reconstruct_data_pipeline.py",
            ),
        ),
    )
    parser.add_argument(
        "--mlflow-log-script",
        default=env(
            "DAILY_INFERENCE_MLFLOW_LOG_SCRIPT",
            first_existing_path(
                "scripts/log_inference_outputs_to_mlflow.py",
                "log_inference_outputs_to_mlflow.py",
            ),
        ),
    )
    return parser


def read_timestamps(path: Path) -> pd.DatetimeIndex:
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path, columns=["timestamp"])
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path, usecols=["timestamp"])
    else:
        raise ValueError(f"Unsupported input format for {path}. Use .parquet or .csv.")
    timestamps = pd.to_datetime(df["timestamp"], errors="coerce").dropna().dt.normalize()
    if timestamps.empty:
        raise ValueError(f"{path} does not contain valid timestamp values.")
    return pd.DatetimeIndex(sorted(timestamps.unique()))


def resolve_origin_dates(
    input_path: Path,
    start_date: str | None,
    end_date: str | None,
    days: int,
) -> list[pd.Timestamp]:
    if days < 1:
        raise ValueError("--days must be >= 1.")

    available_dates = read_timestamps(input_path)
    available_set = set(available_dates)

    if start_date and end_date:
        start = pd.Timestamp(start_date).normalize()
        end = pd.Timestamp(end_date).normalize()
        if start > end:
            raise ValueError("--start-date must be <= --end-date.")
        origins = list(pd.date_range(start=start, end=end, freq="D"))
    elif end_date:
        end = pd.Timestamp(end_date).normalize()
        origins = list(pd.date_range(end=end, periods=days, freq="D"))
    elif start_date:
        start = pd.Timestamp(start_date).normalize()
        origins = list(pd.date_range(start=start, periods=days, freq="D"))
    else:
        end = available_dates.max()
        origins = list(pd.date_range(end=end, periods=days, freq="D"))

    missing = [origin.strftime("%Y-%m-%d") for origin in origins if origin not in available_set]
    if missing:
        raise ValueError(
            "The requested daily inference origins are not present in the input "
            f"dataset: {missing}. Build or backfill inference_daily before running."
        )
    return origins


def parse_codes(repeated_codes: list[str] | None, csv_codes: str | None) -> list[str]:
    codes: list[str] = []
    if repeated_codes:
        codes.extend(repeated_codes)
    if csv_codes:
        codes.extend(item.strip() for item in csv_codes.split(",") if item.strip())
    return list(dict.fromkeys(code for code in codes if not is_internal_metadata_column(code)))


def is_internal_metadata_column(column: str) -> bool:
    return (
        column == "timestamp"
        or column.endswith("___is_imputed")
        or column.endswith("___imputation_method")
        or column.endswith("___imputation_source_last_date")
        or column.endswith("___imputation_created_at")
        or "___imputation_" in column
    )


def read_codes_file(path: str | None) -> list[str]:
    if not path:
        return []
    codes_path = Path(path)
    if not codes_path.exists():
        raise FileNotFoundError(f"Codes file not found: {codes_path}")

    suffix = codes_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(codes_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            raw_codes = payload
        elif isinstance(payload, dict):
            raw_codes = None
            for key in ("codes", "target_codes", "model_codes", "columns"):
                if isinstance(payload.get(key), list):
                    raw_codes = payload[key]
                    break
            if raw_codes is None:
                raise ValueError(
                    f"{codes_path} must contain a JSON list or a dictionary with "
                    "'codes', 'target_codes', 'model_codes' or 'columns'."
                )
        else:
            raise ValueError(f"Unsupported JSON structure in {codes_path}.")
    elif suffix in {".csv", ".tsv"}:
        separator = "\t" if suffix == ".tsv" else ","
        frame = pd.read_csv(codes_path, sep=separator)
        if frame.empty:
            return []
        column_name = "code" if "code" in frame.columns else frame.columns[0]
        raw_codes = frame[column_name].tolist()
    else:
        raw_codes = []
        for line in codes_path.read_text(encoding="utf-8").splitlines():
            raw_codes.extend(part.strip() for part in line.split(","))

    codes = [str(code).strip() for code in raw_codes if str(code).strip()]
    return list(dict.fromkeys(code for code in codes if not is_internal_metadata_column(code)))


def read_input_columns(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        try:
            import pyarrow.parquet as pq

            return pq.ParquetFile(path).schema.names
        except Exception:
            return pd.read_parquet(path).columns.tolist()
    if suffix == ".csv":
        return pd.read_csv(path, nrows=0).columns.tolist()
    raise ValueError(f"Unsupported input format for {path}. Use .parquet or .csv.")


def code_aliases(code: str) -> list[str]:
    candidates = [code]
    if "#" in code:
        candidates.append(code.replace("#", ":"))
    if code.startswith("DEMAND_") and not code.startswith("DEMAND__"):
        candidates.append("DEMAND__" + code[len("DEMAND_") :])
    if not code.startswith("DEMAND_"):
        candidates.append("DEMAND__" + code)
        candidates.append("DEMAND_" + code)
    return list(dict.fromkeys(candidates))


def discover_codes(input_path: Path, model_folder: Path) -> list[str]:
    input_codes = [
        column
        for column in read_input_columns(input_path)
        if not is_internal_metadata_column(column)
    ]
    if not model_folder.exists():
        return input_codes

    model_codes = {path.name for path in model_folder.iterdir() if path.is_dir()}
    if not model_codes:
        return input_codes

    matched_codes = [
        code
        for code in input_codes
        if any(alias in model_codes for alias in code_aliases(code))
    ]
    return matched_codes or input_codes


def chunk_codes(codes: list[str], workers: int, codes_per_worker: int = 0) -> list[list[str]]:
    if workers < 1:
        raise ValueError("--workers must be >= 1.")
    if codes_per_worker < 0:
        raise ValueError("--codes-per-worker must be >= 0.")
    if not codes:
        return []
    chunk_size = codes_per_worker or max(1, ceil(len(codes) / workers))
    return [codes[index : index + chunk_size] for index in range(0, len(codes), chunk_size)]


def write_codes_json(path: Path, codes: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(codes, indent=2), encoding="utf-8")
    return path


def run_command(
    command: list[str],
    pythonpath_prefix: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    printable = " ".join(command)
    print(f"\n$ {printable}", flush=True)
    child_env = os.environ.copy()
    if extra_env:
        child_env.update(extra_env)
    if pythonpath_prefix:
        current_pythonpath = child_env.get("PYTHONPATH")
        child_env["PYTHONPATH"] = (
            pythonpath_prefix
            if not current_pythonpath
            else pythonpath_prefix + os.pathsep + current_pythonpath
        )
    return subprocess.run(command, check=False, text=True, env=child_env)


def append_code_args(command: list[str], codes: list[str]) -> None:
    for code in codes:
        command.extend(["--code", code])


def write_summary(summary_path: Path, rows: list[dict[str, str]]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "prediction_origin_date",
        "status",
        "target_codes",
        "workers",
        "duration_seconds",
        "output_prefix",
        "wide_csv",
        "mlflow_run_name",
        "error",
    ]
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    json_path = summary_path.with_suffix(".json")
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def log_status_to_mlflow(
    args: argparse.Namespace,
    run_name: str,
    status: str,
    row: dict[str, str],
    batch_label: str,
) -> None:
    try:
        import mlflow

        mlflow.set_tracking_uri(args.tracking_uri)
        mlflow.set_experiment(args.experiment_name)
        with mlflow.start_run(run_name=run_name):
            mlflow.log_params(
                {
                    "run_kind": "daily_inference",
                    "status": status,
                    "prediction_origin_date": row.get("prediction_origin_date", ""),
                    "batch_label": batch_label,
                    "output_prefix": row.get("output_prefix", ""),
                    "predictions_root": args.predictions_root,
                    "target_codes": row.get("target_codes", ""),
                    "workers": row.get("workers", ""),
                    "error": row.get("error", ""),
                }
            )
            try:
                mlflow.log_metric("duration_seconds", float(row.get("duration_seconds") or 0.0))
            except ValueError:
                pass
    except Exception as error:
        print(f"Could not log {status} status to MLflow: {error}", flush=True)


def origin_output_paths(predictions_root: Path, output_subdir: str, origin_text: str) -> dict[str, str]:
    output_prefix = f"{output_subdir}/{origin_text}/final_output_predictions"
    base_dir = predictions_root / output_subdir / origin_text
    return {
        "output_prefix": output_prefix,
        "output_path": str(predictions_root / output_prefix),
        "selected_long_path": str(base_dir / "final_output_predictions_selected_long.parquet"),
        "wide_path": str(base_dir / "final_output_predictions_wide.parquet"),
        "wide_csv_path": str(base_dir / "final_output_predictions_wide.csv"),
    }


def build_inference_command(
    args: argparse.Namespace,
    origin_text: str,
    paths: dict[str, str],
    codes_file: Path | None,
    allow_empty_output: bool = False,
) -> list[str]:
    command = [
        sys.executable,
        args.inference_script,
        "--input-directory",
        args.input_directory,
        "--old-input-directory",
        args.old_input_directory,
        "--model-folder",
        args.model_folder,
        "--output-path",
        paths["output_path"],
        "--metrics-df-path",
        args.metrics_df_path,
        "--diagnostic-covariates-path",
        args.diagnostic_covariates_path,
        "--model-selection-metrics-dir",
        args.model_selection_metrics_dir,
        "--lookback-list",
        args.lookback_list,
        "--forecast-list",
        args.forecast_list,
        "--prediction-origin-date",
        origin_text,
        "--selected-long-output-path",
        paths["selected_long_path"],
        "--wide-output-path",
        paths["wide_path"],
        "--wide-csv-output-path",
        paths["wide_csv_path"],
    ]
    if codes_file is not None:
        command.extend(["--codes-file", str(codes_file)])
    if allow_empty_output:
        command.append("--allow-empty-output")
    return command


def tensorflow_worker_env(args: argparse.Namespace) -> dict[str, str]:
    extra_env: dict[str, str] = {}
    if args.workers > 1:
        extra_env["TF_NUM_INTRAOP_THREADS"] = str(args.tf_intra_op_threads or "1")
        extra_env["TF_NUM_INTEROP_THREADS"] = str(args.tf_inter_op_threads or "1")
    else:
        if args.tf_intra_op_threads:
            extra_env["TF_NUM_INTRAOP_THREADS"] = str(args.tf_intra_op_threads)
        if args.tf_inter_op_threads:
            extra_env["TF_NUM_INTEROP_THREADS"] = str(args.tf_inter_op_threads)
    return extra_env


def remove_scoped_path(path: Path, root: Path) -> None:
    if not path.exists():
        return
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError(f"Refusing to remove path outside predictions root: {resolved_path}")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def read_partitioned_prediction_dataset(path: Path) -> pd.DataFrame:
    if path.is_file():
        return pd.read_parquet(path)

    import pyarrow as pa
    import pyarrow.dataset as ds

    dataset = ds.dataset(
        str(path),
        format="parquet",
        partitioning=ds.partitioning(pa.schema([("code", pa.string())])),
    )
    return dataset.to_table().to_pandas()


def merge_shard_outputs(
    args: argparse.Namespace,
    predictions_root: Path,
    final_paths: dict[str, str],
    shard_raw_paths: list[Path],
    shards_root: Path,
) -> None:
    frames = []
    for raw_path in shard_raw_paths:
        if raw_path.exists():
            frames.append(read_partitioned_prediction_dataset(raw_path))

    if not frames:
        raise ValueError("No shard prediction outputs were produced.")
    print(
        f"Merging {len(frames)}/{len(shard_raw_paths)} shards with prediction outputs.",
        flush=True,
    )

    final_output_df = pd.concat(frames, ignore_index=True)
    sort_columns = [
        column
        for column in ("prediction_origin_date", "code", "forecast", "lookback", "target_date")
        if column in final_output_df.columns
    ]
    if sort_columns:
        final_output_df = final_output_df.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)

    inference_package_root = Path(args.inference_script).parent.parent
    if str(inference_package_root) not in sys.path:
        sys.path.insert(0, str(inference_package_root))
    from production.output_formatting import (
        build_historical_like_forecast_table,
        save_table,
        select_stitched_predictions,
    )

    selected_long_df = select_stitched_predictions(final_output_df)
    wide_df = build_historical_like_forecast_table(selected_long_df)

    import pyarrow as pa
    import pyarrow.dataset as ds

    raw_output_path = Path(final_paths["output_path"])
    remove_scoped_path(raw_output_path, predictions_root)
    table = pa.Table.from_pandas(final_output_df, preserve_index=False)
    ds.write_dataset(
        table,
        base_dir=str(raw_output_path),
        format="parquet",
        partitioning=["code"],
        existing_data_behavior="overwrite_or_ignore",
    )

    save_table(selected_long_df, final_paths["selected_long_path"])
    save_table(wide_df, final_paths["wide_path"])
    save_table(wide_df, final_paths["wide_csv_path"])

    if not args.keep_shards:
        remove_scoped_path(shards_root, predictions_root)

    print(f"Merged {len(shard_raw_paths)} shards into {raw_output_path}")
    print(f"Saved {len(final_output_df)} prediction rows to {raw_output_path}")
    print(f"Saved {len(selected_long_df)} stitched rows to {final_paths['selected_long_path']}")
    print(f"Saved historical-like forecast table to {final_paths['wide_path']}")


def run_inference_for_origin(
    args: argparse.Namespace,
    origin_text: str,
    predictions_root: Path,
    output_subdir: str,
    codes: list[str],
) -> tuple[int, dict[str, str]]:
    final_paths = origin_output_paths(predictions_root, output_subdir, origin_text)
    inference_package_root = str(Path(args.inference_script).parent.parent)
    extra_env = tensorflow_worker_env(args)

    if args.workers == 1 or len(codes) <= 1:
        codes_file = None
        if codes:
            codes_file = write_codes_json(
                predictions_root / output_subdir / origin_text / "_run_codes.json",
                codes,
            )
        command = build_inference_command(args, origin_text, final_paths, codes_file)
        result = run_command(command, pythonpath_prefix=inference_package_root, extra_env=extra_env)
        if codes_file and not args.keep_shards:
            remove_scoped_path(codes_file, predictions_root)
        return result.returncode, final_paths

    code_chunks = chunk_codes(codes, args.workers, args.codes_per_worker)
    shards_root = predictions_root / output_subdir / origin_text / "_shards"
    remove_scoped_path(shards_root, predictions_root)
    print(
        f"Parallel inference for {origin_text}: {len(codes)} codes, "
        f"{len(code_chunks)} shards, {min(args.workers, len(code_chunks))} workers.",
        flush=True,
    )

    shard_raw_paths: list[Path] = []
    with ThreadPoolExecutor(max_workers=min(args.workers, len(code_chunks))) as executor:
        futures = {}
        for shard_index, chunk in enumerate(code_chunks, start=1):
            shard_name = f"shard_{shard_index:03d}"
            shard_base = shards_root / shard_name
            shard_paths = {
                "output_prefix": f"{output_subdir}/{origin_text}/_shards/{shard_name}/final_output_predictions",
                "output_path": str(shard_base / "final_output_predictions"),
                "selected_long_path": str(shard_base / "final_output_predictions_selected_long.parquet"),
                "wide_path": str(shard_base / "final_output_predictions_wide.parquet"),
                "wide_csv_path": str(shard_base / "final_output_predictions_wide.csv"),
            }
            codes_file = write_codes_json(shard_base / "codes.json", chunk)
            command = build_inference_command(
                args,
                origin_text,
                shard_paths,
                codes_file,
                allow_empty_output=True,
            )
            shard_raw_paths.append(Path(shard_paths["output_path"]))
            print(
                f"Starting {shard_name}: {len(chunk)} codes "
                f"({chunk[0]} ... {chunk[-1]})",
                flush=True,
            )
            futures[executor.submit(
                run_command,
                command,
                inference_package_root,
                extra_env,
            )] = shard_name

        failed: list[str] = []
        for future in as_completed(futures):
            shard_name = futures[future]
            try:
                result = future.result()
            except Exception as error:
                failed.append(f"{shard_name} wrapper error: {error}")
                continue
            if result.returncode != 0:
                failed.append(f"{shard_name} exit code {result.returncode}")
            else:
                print(f"Completed {shard_name}", flush=True)

    if failed:
        print("Failed inference shards:")
        for failure in failed:
            print(f"- {failure}")
        return 1, final_paths

    merge_shard_outputs(args, predictions_root, final_paths, shard_raw_paths, shards_root)
    return 0, final_paths


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input_directory)
    predictions_root = Path(args.predictions_root)
    origins = resolve_origin_dates(input_path, args.start_date, args.end_date, args.days)
    explicit_codes = parse_codes(args.repeated_codes, None)
    env_codes = parse_codes(None, args.csv_codes)
    file_codes = read_codes_file(args.codes_file)
    codes = list(dict.fromkeys(explicit_codes + env_codes + file_codes))
    code_source = "provided"
    if not codes:
        codes = discover_codes(input_path, Path(args.model_folder))
        code_source = "discovered from input/model folders"
    if not codes:
        raise ValueError("No codes were provided or discovered in the input/model folders.")

    output_subdir = args.output_subdir.strip("/\\")
    batch_label = args.batch_label or datetime.now(timezone.utc).strftime("daily_%Y%m%dT%H%M%SZ")
    summary_rows: list[dict[str, str]] = []

    print("Daily inference origins:")
    for origin in origins:
        print(f"- {origin.strftime('%Y-%m-%d')}")
    if len(codes) <= 20:
        print(f"Target codes ({len(codes)}, {code_source}): {', '.join(codes)}")
    else:
        print(
            f"Target codes ({len(codes)}, {code_source}): "
            f"{codes[0]} ... {codes[-1]}"
        )
    print(f"Inference workers: {args.workers}")

    for origin in origins:
        started_at = time.perf_counter()
        origin_text = origin.strftime("%Y-%m-%d")
        final_paths = origin_output_paths(predictions_root, output_subdir, origin_text)
        output_prefix = final_paths["output_prefix"]
        wide_csv_path = final_paths["wide_csv_path"]
        mlflow_run_name = f"daily_inference_{origin_text}"

        row = {
            "prediction_origin_date": origin_text,
            "status": "started",
            "target_codes": str(len(codes)),
            "workers": str(args.workers),
            "duration_seconds": "",
            "output_prefix": output_prefix,
            "wide_csv": wide_csv_path,
            "mlflow_run_name": mlflow_run_name,
            "error": "",
        }

        returncode, final_paths = run_inference_for_origin(
            args=args,
            origin_text=origin_text,
            predictions_root=predictions_root,
            output_subdir=output_subdir,
            codes=codes,
        )
        row["duration_seconds"] = f"{time.perf_counter() - started_at:.1f}"
        if returncode != 0:
            row["status"] = "failed_inference"
            row["error"] = f"inference exit code {returncode}"
            if not args.skip_mlflow:
                log_status_to_mlflow(
                    args=args,
                    run_name=f"{mlflow_run_name}_failed",
                    status=row["status"],
                    row=row,
                    batch_label=batch_label,
                )
            summary_rows.append(row)
            if not args.continue_on_error:
                write_summary(predictions_root / output_subdir / "daily_inference_summary.csv", summary_rows)
                return returncode
            continue

        if not args.skip_mlflow:
            mlflow_command = [
                sys.executable,
                args.mlflow_log_script,
                "--tracking-uri",
                args.tracking_uri,
                "--experiment-name",
                args.experiment_name,
                "--run-name",
                mlflow_run_name,
                "--predictions-root",
                args.predictions_root,
                "--output-prefix",
                output_prefix,
                "--prediction-origin-date",
                origin_text,
                "--batch-label",
                batch_label,
            ]
            log_result = run_command(mlflow_command)
            row["duration_seconds"] = f"{time.perf_counter() - started_at:.1f}"
            if log_result.returncode != 0:
                row["status"] = "failed_mlflow"
                row["error"] = f"mlflow logging exit code {log_result.returncode}"
                summary_rows.append(row)
                if not args.continue_on_error:
                    write_summary(predictions_root / output_subdir / "daily_inference_summary.csv", summary_rows)
                    return log_result.returncode
                continue

        row["status"] = "ok"
        summary_rows.append(row)

    summary_path = predictions_root / output_subdir / "daily_inference_summary.csv"
    write_summary(summary_path, summary_rows)
    print(f"\nSaved daily inference summary to {summary_path}")
    ok_count = sum(row["status"] == "ok" for row in summary_rows)
    print(f"Completed {ok_count}/{len(summary_rows)} daily inference runs.")
    return 0 if ok_count == len(summary_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
