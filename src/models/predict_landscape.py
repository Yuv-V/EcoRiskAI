"""Score the trained model across every grid cell in the study area.

Phase 3 of the TNC feedback: move from predicting only on the sampled/burned
training cells to a wall-to-wall risk surface. The dense per-cell feature table
is produced by the Earth Engine extraction in ``earth_engine/extract_full_grid.js``
and dropped at ``paths.landscape_features_csv``. This module cleans that table
the same way as training data and applies the trained model to *all* cells.

It is intentionally non-breaking: if the full-grid features CSV is absent, it
logs and returns ``None`` without touching the sampled-prediction outputs.
"""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.dataset.labels import add_prior_month_features
from src.models.predict import (
    OUTPUT_COLUMNS,
    heuristic_risk_probability,
    risk_level,
    suggested_action,
    _should_use_model,
)
from src.models.train import FEATURE_COLUMNS, get_model_features
from src.utils.config import load_config, resolve_project_path
from src.utils.logger import setup_logger

CONTEXT_COLUMNS = ["grid_id", "year", "month", "latitude", "longitude"]


def _prepare_landscape_frame(df: pd.DataFrame, invalid_value: float) -> pd.DataFrame:
    """Clean a raw full-grid export the same way as the training features."""
    df = df.replace(invalid_value, np.nan)

    for column in FEATURE_COLUMNS + CONTEXT_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=[c for c in FEATURE_COLUMNS + CONTEXT_COLUMNS if c in df.columns])
    if "forested_2000" in df.columns:
        df = df[df["forested_2000"] == 1].copy()

    df, _ = add_prior_month_features(df)
    return df.reset_index(drop=True)


def run_landscape_prediction(config: dict[str, Any] | None = None) -> Path | None:
    """Score the trained model on the full-grid feature table, if present."""
    logger = setup_logger(__name__)
    config = config or load_config()

    features_key = config["paths"].get("landscape_features_csv")
    output_key = config["paths"].get("landscape_predictions_csv")
    if not features_key or not output_key:
        logger.info("No landscape paths configured; skipping full-landscape scoring.")
        return None

    features_path = resolve_project_path(features_key)
    output_path = resolve_project_path(output_key)
    model_path = resolve_project_path(config["paths"]["model_path"])
    metrics_path = resolve_project_path(config["paths"]["metrics_path"])
    invalid_value = config.get("data", {}).get("invalid_value", -9999)

    if not features_path.exists():
        logger.info(
            "Full-grid features not found at %s. Run the Earth Engine extraction "
            "(earth_engine/extract_full_grid.js) to enable the wall-to-wall map.",
            features_path,
        )
        return None

    raw = pd.read_csv(features_path)
    missing = [c for c in FEATURE_COLUMNS + CONTEXT_COLUMNS if c not in raw.columns]
    if missing:
        logger.error("Full-grid features are missing columns: %s", missing)
        return None

    df = _prepare_landscape_frame(raw, invalid_value)
    if df.empty:
        logger.error("Full-grid features have no valid forested rows after cleaning.")
        return None

    model_features = get_model_features(df, config)
    prediction_source = "heuristic_mvp_risk"
    if _should_use_model(metrics_path, model_path):
        try:
            import joblib

            model = joblib.load(model_path)
            probabilities = model.predict_proba(df[model_features])[:, 1]
            prediction_source = "xgboost"
            logger.info("Scoring %s landscape cells with the trained model.", len(df))
        except Exception as error:  # noqa: BLE001 - fall back rather than crash the pipeline
            logger.warning("Could not use model (%s). Using heuristic MVP risk.", error)
            probabilities = heuristic_risk_probability(df)
    else:
        logger.warning("No trained model available. Using heuristic MVP risk for landscape.")
        probabilities = heuristic_risk_probability(df)

    out = df[CONTEXT_COLUMNS].copy()
    out["predicted_risk_probability"] = probabilities
    out["predicted_risk_level"] = out["predicted_risk_probability"].apply(risk_level)
    out["suggested_action"] = out["predicted_risk_level"].apply(suggested_action)
    out["prediction_source"] = prediction_source
    for column in ["ndvi", "ndmi", "nbr", "soil_moisture", "precipitation",
                   "temperature_c", "burned_this_month", "night_lights"]:
        out[column] = df[column] if column in df.columns else np.nan

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out[OUTPUT_COLUMNS + ["prediction_source"]].to_csv(output_path, index=False)
    logger.info("Saved full-landscape predictions to %s (%s cells).", output_path, len(out))
    return output_path


def main() -> None:
    """Run full-landscape scoring as a script."""
    run_landscape_prediction()


if __name__ == "__main__":
    main()
