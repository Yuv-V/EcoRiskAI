"""Train the EcoRiskAI XGBoost baseline model."""

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.config import load_config, resolve_project_path
from src.utils.logger import setup_logger


# Required model features. Every row must have all of these to be modeled.
#
# NOTE: ``burned_this_month`` was removed on purpose (TNC check-in, Jul 2026).
# A concurrent burn flag co-occurs with 100% of positive labels, so it lets the
# model shortcut "it burned -> loss" instead of learning the pre-burn conditions
# that make a place risky. The remaining spectral/climate/terrain signals are
# what we actually want the model to reason over. The column is still carried in
# the data and shown in the dashboard; it is just not a model input.
FEATURE_COLUMNS = [
    "blue",
    "green",
    "red",
    "nir",
    "swir1",
    "swir2",
    "ndvi",
    "ndmi",
    "nbr",
    "treecover2000",
    "elevation",
    "slope",
    "aspect",
    "soil_moisture",
    "precipitation",
    "temperature_c",
    "night_lights",
    "landsat_image_count",
]

# Optional "month before" change features. NaN-tolerant, so they are not part of
# the required set above. Coverage is currently low (sparse monthly export), so
# they are only fed to the model when labeling.use_prior_month_features is true.
LAG_FEATURE_COLUMNS = ["ndvi_delta_1m", "ndmi_delta_1m", "nbr_delta_1m", "soil_moisture_delta_1m"]

TARGET_COLUMN = "forest_loss_next_year"


def get_model_features(df: pd.DataFrame, config: dict[str, Any] | None = None) -> list[str]:
    """Return the model feature list, adding lag features only when enabled."""
    use_lag = bool((config or {}).get("labeling", {}).get("use_prior_month_features", False))
    if use_lag:
        present = [column for column in LAG_FEATURE_COLUMNS if column in df.columns]
        return FEATURE_COLUMNS + present
    return list(FEATURE_COLUMNS)


def _write_metrics(metrics_path: Path, metrics: dict[str, Any]) -> None:
    """Write model metrics and training status as JSON."""
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def _heuristic_metrics(reason: str) -> dict[str, Any]:
    """Create metadata for a heuristic-only MVP run."""
    return {
        "model_type": "heuristic_mvp_risk",
        "trained": False,
        "reason": reason,
        "accuracy": None,
        "precision": None,
        "recall": None,
        "f1": None,
        "roc_auc": None,
    }


def run_training(config: dict[str, Any] | None = None) -> Path | None:
    """Train XGBoost when labels allow it, otherwise mark heuristic fallback."""
    logger = setup_logger(__name__)
    config = config or load_config()

    feature_path = resolve_project_path(config["paths"]["clean_features_csv"])
    model_path = resolve_project_path(config["paths"]["model_path"])
    metrics_path = resolve_project_path(config["paths"]["metrics_path"])
    training_years = config.get("data", {}).get("training_years", [2020, 2021, 2022, 2023])
    random_state = config.get("model", {}).get("random_state", 42)
    test_size = config.get("model", {}).get("test_size", 0.2)

    if not feature_path.exists():
        logger.error(
            "Clean feature table not found at %s. Run dataset building first.",
            feature_path,
        )
        _write_metrics(metrics_path, _heuristic_metrics("Clean feature table is missing."))
        return None

    try:
        import joblib
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )
        from sklearn.model_selection import train_test_split
        from xgboost import XGBClassifier
    except ModuleNotFoundError as error:
        logger.error(
            "Missing dependency %s. Predictions will use heuristic MVP risk.",
            error.name,
        )
        _write_metrics(metrics_path, _heuristic_metrics(f"Missing dependency: {error.name}"))
        return None

    df = pd.read_csv(feature_path)
    missing_columns = [
        column for column in FEATURE_COLUMNS + [TARGET_COLUMN, "year"] if column not in df.columns
    ]
    if missing_columns:
        logger.error("Feature table is missing columns: %s", missing_columns)
        _write_metrics(metrics_path, _heuristic_metrics(f"Missing columns: {missing_columns}"))
        return None

    train_df = df[df["year"].isin(training_years)].copy()
    train_df = train_df[train_df[TARGET_COLUMN].isin([0, 1])].copy()
    if train_df.empty:
        logger.error("No training rows found for years %s.", training_years)
        _write_metrics(metrics_path, _heuristic_metrics("No labeled training rows found."))
        return None

    if train_df[TARGET_COLUMN].nunique() < 2:
        logger.error("Training target needs both 0 and 1 classes. Predictions will use heuristic MVP risk.")
        _write_metrics(metrics_path, _heuristic_metrics("Training labels contain fewer than two classes."))
        return None

    model_features = get_model_features(df, config)
    x = train_df[model_features]
    y = train_df[TARGET_COLUMN].astype(int)

    class_counts = y.value_counts()
    stratify = y if len(class_counts) == 2 and class_counts.min() >= 2 else None
    negative_count = int(class_counts.get(0, 0))
    positive_count = int(class_counts.get(1, 0))
    scale_pos_weight = negative_count / positive_count if positive_count else 1.0

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        scale_pos_weight=scale_pos_weight,
        random_state=random_state,
    )
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    probabilities = model.predict_proba(x_test)[:, 1]
    try:
        roc_auc = roc_auc_score(y_test, probabilities)
    except ValueError:
        logger.warning("ROC-AUC is undefined because y_test contains one class.")
        roc_auc = float("nan")

    # Feature importances, so the dashboard can show "what drives the score"
    # without loading the model at runtime.
    feature_importances = {
        feature: float(importance)
        for feature, importance in zip(model_features, model.feature_importances_)
    }

    metrics = {
        "model_type": "xgboost",
        "target": TARGET_COLUMN,
        "target_scope": "fire-associated forest loss, next year",
        "n_features": len(model_features),
        "features": model_features,
        "feature_importances": feature_importances,
        "trained": True,
        "training_rows": int(len(train_df)),
        "positive_labels": positive_count,
        "negative_labels": negative_count,
        "scale_pos_weight": scale_pos_weight,
        "accuracy": accuracy_score(y_test, predictions),
        "precision": precision_score(y_test, predictions, zero_division=0),
        "recall": recall_score(y_test, predictions, zero_division=0),
        "f1": f1_score(y_test, predictions, zero_division=0),
        "roc_auc": roc_auc,
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    _write_metrics(metrics_path, metrics)

    logger.info("Saved model to %s", model_path)
    logger.info("Saved metrics to %s", metrics_path)
    logger.info("Metrics: %s", metrics)
    return model_path


def main() -> None:
    """Run model training as a script."""
    run_training()


if __name__ == "__main__":
    main()
