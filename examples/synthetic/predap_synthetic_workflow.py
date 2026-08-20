"""Generate a public synthetic PREDAP data/model/inference workflow.

The script intentionally uses only the Python standard library so it can run in
CI before heavyweight ML dependencies are installed. It does not train the real
Transformer models; it validates the public contracts with a deterministic
dummy model bundle.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean


DEFAULT_CODES = ["DEMAND__TOTAL", "SERVEI_CODI__URG", "DX_A_SYN"]
DEFAULT_FORECASTS = [7, 14, 30]


def synthetic_stage_selection(forecast: int) -> dict[str, str]:
    if forecast <= 7:
        return {
            "model_stage_reached": "univariate",
            "selected_model_type": "univariate_model",
            "model_selection_reason": "synthetic_demo_wape",
            "selected_stage_wape": "9.5000",
            "univariate_wape": "9.5000",
            "diagnostics_wape": "10.2000",
            "seasonal_wape": "10.6000",
        }
    if forecast <= 14:
        return {
            "model_stage_reached": "diagnostics",
            "selected_model_type": "diagnostics_model",
            "model_selection_reason": "synthetic_demo_wape",
            "selected_stage_wape": "12.0000",
            "univariate_wape": "12.7000",
            "diagnostics_wape": "12.0000",
            "seasonal_wape": "12.5000",
        }
    return {
        "model_stage_reached": "seasonal",
        "selected_model_type": "seasonal_model",
        "model_selection_reason": "synthetic_demo_wape",
        "selected_stage_wape": "15.1000",
        "univariate_wape": "16.4000",
        "diagnostics_wape": "15.8000",
        "seasonal_wape": "15.1000",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the public PREDAP synthetic smoke workflow.")
    parser.add_argument("--output-dir", default="runtime/synthetic_demo", help="Directory for generated synthetic outputs.")
    parser.add_argument("--start-date", default="2024-01-01", help="First synthetic historical date.")
    parser.add_argument("--days", type=int, default=180, help="Number of historical days to generate.")
    parser.add_argument("--holdout-days", type=int, default=21, help="Validation tail used for dummy metrics.")
    parser.add_argument("--seed", type=int, default=20260812, help="Deterministic random seed.")
    parser.add_argument("--codes", nargs="*", default=DEFAULT_CODES, help="Synthetic target codes to generate.")
    return parser.parse_args()


def generate_history(start: date, days: int, codes: list[str], seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    rows: list[dict[str, str]] = []
    for day_idx in range(days):
        current = start + timedelta(days=day_idx)
        dow = current.weekday()
        weekend_factor = -26 if dow >= 5 else 0
        weekly = 12 * math.sin(2 * math.pi * day_idx / 7)
        annual = 8 * math.sin(2 * math.pi * day_idx / 365)
        row: dict[str, str] = {"timestamp": current.isoformat()}
        for code_idx, code in enumerate(codes):
            base = 95 + code_idx * 18
            trend = 0.07 * day_idx * (1 + code_idx / 4)
            noise = rng.gauss(0, 2.5 + code_idx)
            value = max(0, base + weekly + annual + weekend_factor + trend + noise)
            row[code] = str(round(value, 2))
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def numeric_series(rows: list[dict[str, str]], code: str) -> list[float]:
    return [float(row[code]) for row in rows]


def train_dummy_model(values: list[float], lookback: int, forecast: int) -> dict[str, float | int | str]:
    tail = values[-lookback:]
    previous = values[-(lookback * 2) : -lookback] if len(values) >= lookback * 2 else values[:lookback]
    level = mean(tail)
    daily_trend = (mean(tail) - mean(previous)) / max(1, lookback)
    residuals = [abs(value - level) for value in tail]
    residual_scale = max(1.0, mean(residuals))
    return {
        "forecast": forecast,
        "lookback": lookback,
        "method": "moving_average_with_trend",
        "level": round(level, 6),
        "daily_trend": round(daily_trend, 6),
        "residual_scale": round(residual_scale, 6),
    }


def predict_from_model(model: dict[str, float | int | str], horizon_day: int) -> tuple[float, float, float]:
    level = float(model["level"])
    trend = float(model["daily_trend"])
    scale = float(model["residual_scale"])
    prediction = max(0.0, level + trend * horizon_day)
    interval = 1.96 * scale
    return (
        round(prediction, 2),
        round(max(0.0, prediction - interval), 2),
        round(prediction + interval, 2),
    )


def write_model_bundle(
    model_dir: Path,
    train_rows: list[dict[str, str]],
    codes: list[str],
    forecasts: list[int],
) -> dict[str, dict[int, dict[str, float | int | str]]]:
    models: dict[str, dict[int, dict[str, float | int | str]]] = {}
    for code in codes:
        code_models: dict[int, dict[str, float | int | str]] = {}
        values = numeric_series(train_rows, code)
        for forecast in forecasts:
            lookback = min(30, max(7, forecast))
            model = train_dummy_model(values, lookback=lookback, forecast=forecast)
            model["code"] = code
            code_models[forecast] = model
            model_path = model_dir / "models" / code / f"forecast_{forecast}_lookback_{lookback}.json"
            model_path.parent.mkdir(parents=True, exist_ok=True)
            model_path.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
        models[code] = code_models

    manifest = {
        "schema_version": "predap-dummy-model-bundle/v1",
        "bundle_type": "synthetic_smoke_test",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target_codes": codes,
        "forecasts": forecasts,
        "lookbacks": sorted({int(model["lookback"]) for code_models in models.values() for model in code_models.values()}),
        "model_format": "json-moving-average",
        "contains_real_data": False,
    }
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return models


def evaluate_holdout(
    train_rows: list[dict[str, str]],
    holdout_rows: list[dict[str, str]],
    codes: list[str],
) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for code in codes:
        values = numeric_series(train_rows, code)
        model = train_dummy_model(values, lookback=min(30, len(values)), forecast=1)
        errors = []
        for idx, row in enumerate(holdout_rows, start=1):
            prediction, _, _ = predict_from_model(model, idx)
            errors.append(prediction - float(row[code]))
        mae = mean(abs(error) for error in errors)
        rmse = math.sqrt(mean(error * error for error in errors))
        metrics[code] = {"mae": round(mae, 4), "rmse": round(rmse, 4)}
    return metrics


def write_predictions(
    output_path: Path,
    train_rows: list[dict[str, str]],
    models: dict[str, dict[int, dict[str, float | int | str]]],
) -> list[dict[str, str]]:
    origin = date.fromisoformat(train_rows[-1]["timestamp"])
    prediction_rows: list[dict[str, str]] = []
    for code, code_models in models.items():
        for forecast, model in sorted(code_models.items()):
            lookback = int(model["lookback"])
            final_forecast_date = origin + timedelta(days=forecast)
            stage_selection = synthetic_stage_selection(forecast)
            for horizon_day in range(1, forecast + 1):
                target_date = origin + timedelta(days=horizon_day)
                prediction, lower, upper = predict_from_model(model, horizon_day)
                prediction_rows.append(
                    {
                        "code": code,
                        "target_date": target_date.isoformat(),
                        "init_forecast_date": origin.isoformat(),
                        "final_forecast_date": final_forecast_date.isoformat(),
                        "prediction_origin_date": origin.isoformat(),
                        "horizon_day": str(horizon_day),
                        "forecast": str(forecast),
                        "lookback": str(lookback),
                        "model_id": f"{code}__{forecast}fh_{lookback}lb",
                        **stage_selection,
                        "predictions": f"{prediction:.2f}",
                        "ci_lower": f"{lower:.2f}",
                        "ci_upper": f"{upper:.2f}",
                        "velocity": f"{float(model['daily_trend']):.4f}",
                        "acceleration": "0.0000",
                    }
                )

    write_csv(
        output_path,
        prediction_rows,
        [
            "code",
            "target_date",
            "init_forecast_date",
            "final_forecast_date",
            "prediction_origin_date",
            "horizon_day",
            "forecast",
            "lookback",
            "model_id",
            "model_stage_reached",
            "selected_model_type",
            "model_selection_reason",
            "selected_stage_wape",
            "univariate_wape",
            "diagnostics_wape",
            "seasonal_wape",
            "predictions",
            "ci_lower",
            "ci_upper",
            "velocity",
            "acceleration",
        ],
    )
    return prediction_rows


def write_wide_predictions(output_path: Path, prediction_rows: list[dict[str, str]], codes: list[str]) -> list[dict[str, str]]:
    selected: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in prediction_rows:
        key = (row["prediction_origin_date"], row["code"], row["target_date"])
        candidate = selected.get(key)
        if candidate is None or (
            int(row["forecast"]),
            int(row["lookback"]),
        ) < (
            int(candidate["forecast"]),
            int(candidate["lookback"]),
        ):
            selected[key] = row

    wide_rows_by_date: dict[tuple[str, str], dict[str, str]] = {}
    for row in selected.values():
        key = (row["prediction_origin_date"], row["target_date"])
        wide_row = wide_rows_by_date.setdefault(
            key,
            {
                "prediction_origin_date": row["prediction_origin_date"],
                "timestamp": row["target_date"],
            },
        )
        code = row["code"]
        wide_row[code] = row["predictions"]
        for column in [
            "ci_lower",
            "ci_upper",
            "velocity",
            "acceleration",
            "forecast",
            "lookback",
            "horizon_day",
            "model_id",
            "model_stage_reached",
            "selected_model_type",
            "model_selection_reason",
            "selected_stage_wape",
            "univariate_wape",
            "diagnostics_wape",
            "seasonal_wape",
        ]:
            wide_row[f"{code}__{column}"] = row[column]

    fieldnames = ["prediction_origin_date", "timestamp", *codes]
    for code in codes:
        for column in [
            "ci_lower",
            "ci_upper",
            "velocity",
            "acceleration",
            "forecast",
            "lookback",
            "horizon_day",
            "model_id",
            "model_stage_reached",
            "selected_model_type",
            "model_selection_reason",
            "selected_stage_wape",
            "univariate_wape",
            "diagnostics_wape",
            "seasonal_wape",
        ]:
            fieldnames.append(f"{code}__{column}")

    wide_rows = [
        wide_rows_by_date[key]
        for key in sorted(wide_rows_by_date, key=lambda item: (item[0], item[1]))
    ]
    write_csv(output_path, wide_rows, fieldnames)
    return wide_rows


def main() -> int:
    args = parse_args()
    if args.days <= args.holdout_days + 30:
        raise ValueError("--days must be at least 31 days larger than --holdout-days.")

    output_dir = Path(args.output_dir)
    retrieval_dir = output_dir / "retrieval_export"
    model_dir = output_dir / "model_bundle"
    inference_dir = output_dir / "inference"

    start = date.fromisoformat(args.start_date)
    rows = generate_history(start=start, days=args.days, codes=args.codes, seed=args.seed)
    split_idx = len(rows) - args.holdout_days
    train_rows = rows[:split_idx]
    holdout_rows = rows[split_idx:]
    fieldnames = ["timestamp", *args.codes]

    write_csv(retrieval_dir / "historical_daily.csv", rows, fieldnames)
    write_csv(retrieval_dir / f"training_until_{train_rows[-1]['timestamp']}.csv", train_rows, fieldnames)
    (retrieval_dir / "target_codes_models_columns_order.json").write_text(
        json.dumps(args.codes, indent=2) + "\n",
        encoding="utf-8",
    )
    (retrieval_dir / "models_columns_orders.txt").write_text("\n".join(args.codes) + "\n", encoding="utf-8")

    metrics = evaluate_holdout(train_rows=train_rows, holdout_rows=holdout_rows, codes=args.codes)
    models = write_model_bundle(model_dir=model_dir, train_rows=train_rows, codes=args.codes, forecasts=DEFAULT_FORECASTS)
    prediction_rows = write_predictions(inference_dir / "predictions.csv", train_rows=train_rows, models=models)
    wide_prediction_rows = write_wide_predictions(
        inference_dir / "predictions_wide.csv",
        prediction_rows=prediction_rows,
        codes=args.codes,
    )

    summary = {
        "contains_real_data": False,
        "rows_generated": len(rows),
        "training_rows": len(train_rows),
        "holdout_rows": len(holdout_rows),
        "prediction_rows": len(prediction_rows),
        "wide_prediction_rows": len(wide_prediction_rows),
        "metrics": metrics,
    }
    (output_dir / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("Synthetic PREDAP workflow completed.")
    print(f"Retrieval export: {retrieval_dir}")
    print(f"Model bundle:     {model_dir}")
    print(f"Predictions:      {inference_dir / 'predictions.csv'}")
    print(f"Wide predictions: {inference_dir / 'predictions_wide.csv'}")
    print(f"Metrics:          {output_dir / 'metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
