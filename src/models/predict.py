"""Generate EcoRiskAI risk predictions from the trained baseline model."""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.models.train import FEATURE_COLUMNS, get_model_features
from src.utils.config import load_config, resolve_project_path
from src.utils.logger import setup_logger


OUTPUT_COLUMNS = [
    "grid_id",
    "year",
    "month",
    "latitude",
    "longitude",
    "predicted_risk_probability",
    "predicted_risk_level",
    "suggested_action",
    "ndvi",
    "ndmi",
    "nbr",
    "soil_moisture",
    "precipitation",
    "temperature_c",
    "burned_this_month",
    "night_lights",
]


def _normalize(series: pd.Series) -> pd.Series:
    """Scale a numeric series to 0-1, returning zeros for constant values."""
    minimum = series.min()
    maximum = series.max()
    if pd.isna(minimum) or pd.isna(maximum) or maximum == minimum:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - minimum) / (maximum - minimum)


def heuristic_risk_probability(df: pd.DataFrame) -> pd.Series:
    """Compute a transparent heuristic MVP risk score from available features."""
    risk_parts = [
        1 - _normalize(df["ndvi"]),
        1 - _normalize(df["ndmi"]),
        1 - _normalize(df["soil_moisture"]),
        _normalize(df["temperature_c"]),
        _normalize(df["burned_this_month"]),
        _normalize(df["night_lights"]),
    ]
    return pd.concat(risk_parts, axis=1).mean(axis=1).clip(0, 1)


def risk_level(probability: float) -> str:
    """Convert a risk probability into a simple dashboard risk level."""
    if probability < 0.33:
        return "Low"
    if probability <= 0.66:
        return "Medium"
    return "High"


def suggested_action(level: str) -> str:
    """Map each risk level to a conservation planning action."""
    actions = {
        "Low": "Continue standard monitoring.",
        "Medium": "Review during seasonal planning.",
        "High": "Prioritize for closer monitoring.",
    }
    return actions[level]


def _should_use_model(metrics_path: Path, model_path: Path) -> bool:
    """Return whether a saved model should be used for predictions."""
    if not model_path.exists() or not metrics_path.exists():
        return False
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return metrics.get("trained") is True and metrics.get("model_type") == "xgboost"


def run_prediction(config: dict[str, Any] | None = None) -> Path | None:
    """Load the trained model and write risk predictions for all valid rows."""
    logger = setup_logger(__name__)
    config = config or load_config()

    feature_path = resolve_project_path(config["paths"]["clean_features_csv"])
    model_path = resolve_project_path(config["paths"]["model_path"])
    metrics_path = resolve_project_path(config["paths"]["metrics_path"])
    predictions_path = resolve_project_path(config["paths"]["predictions_csv"])

    if not feature_path.exists():
        logger.error(
            "Clean feature table not found at %s. Run dataset building first.",
            feature_path,
        )
        return None

    df = pd.read_csv(feature_path)
    required_columns = FEATURE_COLUMNS + ["grid_id", "year", "month", "latitude", "longitude"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        logger.error("Feature table is missing columns: %s", missing_columns)
        return None

    model_features = get_model_features(df, config)
    prediction_source = "heuristic_mvp_risk"
    if _should_use_model(metrics_path, model_path):
        try:
            import joblib

            model = joblib.load(model_path)
            probabilities = model.predict_proba(df[model_features])[:, 1]
            prediction_source = "xgboost"
            logger.info("Using trained XGBoost model for predictions.")
        except ModuleNotFoundError as error:
            logger.warning("Missing dependency %s. Using heuristic MVP risk.", error.name)
            probabilities = heuristic_risk_probability(df)
        except Exception as error:
            logger.warning("Could not load model (%s). Using heuristic MVP risk.", error)
            probabilities = heuristic_risk_probability(df)
    else:
        logger.warning("No trained model available. Using heuristic MVP risk.")
        probabilities = heuristic_risk_probability(df)

    predictions_df = df[["grid_id", "year", "month", "latitude", "longitude"]].copy()
    predictions_df["predicted_risk_probability"] = probabilities
    predictions_df["predicted_risk_level"] = predictions_df["predicted_risk_probability"].apply(risk_level)
    predictions_df["suggested_action"] = predictions_df["predicted_risk_level"].apply(suggested_action)
    predictions_df["prediction_source"] = prediction_source
    for column in [
        "ndvi",
        "ndmi",
        "nbr",
        "soil_moisture",
        "precipitation",
        "temperature_c",
        "burned_this_month",
        "night_lights",
    ]:
        predictions_df[column] = df[column]

    predictions_path.parent.mkdir(parents=True, exist_ok=True)
    output_columns = OUTPUT_COLUMNS + ["prediction_source"]
    predictions_df[output_columns].to_csv(predictions_path, index=False)

    logger.info("Saved predictions to %s", predictions_path)
    logger.info("Prediction rows: %s", len(predictions_df))
    return predictions_path


def main() -> None:
    """Run prediction generation as a script."""
    run_prediction()


if __name__ == "__main__":
    main()
