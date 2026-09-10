"""Clean the merged EcoRiskAI dataset for modeling and prediction."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.dataset.labels import add_prior_month_features, build_fire_loss_label, labeling_config
from src.models.train import FEATURE_COLUMNS, TARGET_COLUMN
from src.utils.config import load_config, resolve_project_path
from src.utils.logger import setup_logger


REQUIRED_CONTEXT_COLUMNS = ["grid_id", "year", "month", "latitude", "longitude", "forested_2000"]
IMPORTANT_COLUMNS = REQUIRED_CONTEXT_COLUMNS + FEATURE_COLUMNS


def run_clean_dataset(config: dict[str, Any] | None = None) -> Path | None:
    """Clean invalid values, keep forested cells, and save model features."""
    logger = setup_logger(__name__)
    config = config or load_config()

    merged_path = resolve_project_path(config["paths"]["merged_csv"])
    clean_path = resolve_project_path(config["paths"]["clean_features_csv"])
    invalid_value = config.get("data", {}).get("invalid_value", -9999)

    if not merged_path.exists():
        logger.error("Merged CSV not found at %s. Run merge_yearly_exports first.", merged_path)
        return None

    df = pd.read_csv(merged_path)
    missing_columns = [column for column in IMPORTANT_COLUMNS if column not in df.columns]
    if missing_columns:
        logger.error("Merged CSV is missing required columns: %s", missing_columns)
        return None

    # Rebuild the target as a fire-scoped, date-anchored label (TNC feedback):
    # forest loss recorded `lookahead_years` later AND associated with a burn, so
    # timber-harvest loss does not pollute a wildfire-risk model.
    label_options = labeling_config(config)
    if "lossyear" in df.columns:
        original_positive = int(pd.to_numeric(df.get(TARGET_COLUMN), errors="coerce").fillna(0).eq(1).sum())
        df[TARGET_COLUMN] = build_fire_loss_label(
            df,
            lookahead_years=label_options["lookahead_years"],
            fire_scoped=label_options["fire_scoped"],
        )
        fire_positive = int(df[TARGET_COLUMN].eq(1).sum())
        logger.info(
            "Fire-scoped label: %s positives (was %s; %s non-fire loss positives excluded).",
            fire_positive,
            original_positive,
            max(original_positive - fire_positive, 0),
        )

    clean_df = df.copy()
    clean_df = clean_df.replace(invalid_value, np.nan)

    numeric_columns = IMPORTANT_COLUMNS + ([TARGET_COLUMN] if TARGET_COLUMN in clean_df.columns else [])
    for column in numeric_columns:
        clean_df[column] = pd.to_numeric(clean_df[column], errors="coerce")

    before_count = len(clean_df)
    clean_df = clean_df.dropna(subset=IMPORTANT_COLUMNS)
    clean_df = clean_df[clean_df["forested_2000"] == 1].copy()

    if TARGET_COLUMN in clean_df.columns:
        valid_labels = clean_df[TARGET_COLUMN].isin([0, 1])
        clean_df.loc[~valid_labels, TARGET_COLUMN] = np.nan

    # Add "month before" change features per grid cell. These stay in the table
    # for inspection and are only used by the model when enabled in config; on
    # the current sparse export their coverage is low (see ROADMAP Phase 3).
    clean_df, lag_columns = add_prior_month_features(clean_df)
    if lag_columns:
        coverage = float(clean_df[lag_columns[0]].notna().mean())
        logger.info(
            "Added month-before features %s (coverage ~%.0f%%; model use=%s).",
            lag_columns,
            coverage * 100,
            label_options["use_prior_month_features"],
        )

    clean_path.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(clean_path, index=False)

    labeled_count = int(clean_df[TARGET_COLUMN].isin([0, 1]).sum()) if TARGET_COLUMN in clean_df.columns else 0
    logger.info("Saved clean features to %s", clean_path)
    logger.info("Clean rows: %s; dropped rows: %s; labeled rows: %s", len(clean_df), before_count - len(clean_df), labeled_count)
    return clean_path


def main() -> None:
    """Run dataset cleaning as a script."""
    run_clean_dataset()


if __name__ == "__main__":
    main()
