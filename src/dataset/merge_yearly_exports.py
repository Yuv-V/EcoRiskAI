"""Merge yearly Earth Engine CSV exports into one master table."""

from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.config import load_config, resolve_project_path
from src.utils.logger import setup_logger


def run_merge_yearly_exports(config: dict[str, Any] | None = None) -> Path | None:
    """Concatenate yearly CSV exports and save a deduplicated merged CSV."""
    logger = setup_logger(__name__)
    config = config or load_config()

    exports_dir = resolve_project_path(config["paths"]["yearly_exports_dir"])
    merged_path = resolve_project_path(config["paths"]["merged_csv"])

    if not exports_dir.exists():
        logger.error(
            "Yearly exports directory not found at %s. Add CSVs before running.",
            exports_dir,
        )
        return None

    csv_paths = sorted(exports_dir.glob("*.csv"))
    if not csv_paths:
        logger.error("No yearly CSV exports found in %s.", exports_dir)
        return None

    frames = []
    for csv_path in csv_paths:
        logger.info("Reading yearly export: %s", csv_path.name)
        frames.append(pd.read_csv(csv_path))

    merged_df = pd.concat(frames, ignore_index=True)
    before_count = len(merged_df)
    merged_df = merged_df.drop_duplicates(subset=["grid_id", "year", "month"])
    merged_df = merged_df.sort_values(["grid_id", "year", "month"]).reset_index(drop=True)

    merged_path.parent.mkdir(parents=True, exist_ok=True)
    merged_df.to_csv(merged_path, index=False)

    logger.info("Saved merged CSV to %s", merged_path)
    logger.info("Merged rows: %s; removed duplicates: %s", len(merged_df), before_count - len(merged_df))
    return merged_path


def main() -> None:
    """Run yearly export merging as a script."""
    run_merge_yearly_exports()


if __name__ == "__main__":
    main()
