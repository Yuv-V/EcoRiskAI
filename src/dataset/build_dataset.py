"""Build the cleaned EcoRiskAI feature table."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.utils.config import load_config, resolve_project_path
from src.utils.logger import setup_logger


EXPECTED_COLUMNS = [
    "grid_id",
    "year",
    "month",
    "latitude",
    "longitude",
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
    "lossyear",
    "forest_loss_next_year",
    "forested_2000",
    "elevation",
    "slope",
    "aspect",
    "soil_moisture",
    "precipitation",
    "temperature_c",
    "burned_this_month",
    "night_lights",
    "landsat_image_count",
]


def _validate_columns(df: pd.DataFrame) -> list[str]:
    """Return expected columns that are missing from the dataframe."""
    return [column for column in EXPECTED_COLUMNS if column not in df.columns]


def clean_master_dataframe(df: pd.DataFrame, invalid_value: int | float) -> pd.DataFrame:
    """Clean invalid sentinels and keep rows with binary target labels."""
    clean_df = df.copy()
    clean_df = clean_df.replace(invalid_value, np.nan)
    clean_df = clean_df.dropna(subset=EXPECTED_COLUMNS)
    clean_df = clean_df[clean_df["forest_loss_next_year"].isin([0, 1])]
    clean_df["forest_loss_next_year"] = clean_df["forest_loss_next_year"].astype(int)
    return clean_df


def run_build_dataset(config: dict[str, Any] | None = None) -> Path | None:
    """Create and save the cleaned feature table."""
    logger = setup_logger(__name__)
    config = config or load_config()

    raw_path = resolve_project_path(config["paths"]["raw_master_csv"])
    output_path = resolve_project_path(config["paths"]["processed_feature_table"])
    model_ready_dir = resolve_project_path(config["paths"]["model_ready_dir"])
    invalid_value = config.get("data", {}).get("invalid_value", -9999)

    if not raw_path.exists():
        logger.error(
            "Master CSV not found at %s. Place the file there before building data.",
            raw_path,
        )
        return None

    df = pd.read_csv(raw_path)
    missing_columns = _validate_columns(df)
    if missing_columns:
        logger.error("Master CSV is missing expected columns: %s", missing_columns)
        return None

    clean_df = clean_master_dataframe(df, invalid_value)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model_ready_dir.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(output_path, index=False)

    logger.info("Saved cleaned feature table to %s", output_path)
    logger.info("Cleaned shape: %s", clean_df.shape)
    return output_path


def main() -> None:
    """Run dataset building as a script."""
    run_build_dataset()


if __name__ == "__main__":
    main()
