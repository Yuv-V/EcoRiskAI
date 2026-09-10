"""Inspect the EcoRiskAI master CSV exported from Google Earth Engine."""

from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.config import load_config, resolve_project_path
from src.utils.logger import setup_logger


def _format_series(series: pd.Series) -> str:
    """Format a pandas Series for readable logging."""
    return series.to_string()


def run_inspection(config: dict[str, Any] | None = None) -> bool:
    """Load the master CSV and log core dataset diagnostics."""
    logger = setup_logger(__name__)
    config = config or load_config()
    csv_path = resolve_project_path(config["paths"]["raw_master_csv"])

    if not csv_path.exists():
        logger.error(
            "Master CSV not found at %s. Place the file there before running inspection.",
            csv_path,
        )
        return False

    df = pd.read_csv(csv_path)

    logger.info("Shape: %s", df.shape)
    logger.info("Columns: %s", list(df.columns))
    logger.info("Missing values:\n%s", _format_series(df.isna().sum()))
    logger.info("Basic stats:\n%s", df.describe(include="all").to_string())

    if {"year", "month"}.issubset(df.columns):
        rows_per_period = df.groupby(["year", "month"]).size()
        logger.info("Rows per year/month:\n%s", _format_series(rows_per_period))
    else:
        logger.warning("Cannot show rows per year/month because year or month is missing.")

    if "forest_loss_next_year" in df.columns:
        label_distribution = df["forest_loss_next_year"].value_counts(
            dropna=False
        ).sort_index()
        logger.info("Label distribution:\n%s", _format_series(label_distribution))
    else:
        logger.warning("Cannot show label distribution because target column is missing.")

    return True


def main() -> None:
    """Run master CSV inspection as a script."""
    run_inspection()


if __name__ == "__main__":
    main()
