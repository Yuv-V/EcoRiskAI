"""Conservation prioritization signals (decision support, not model inputs).

The July 2026 TNC check-in surfaced factors that experts actually use to decide
*where to act* — distinct from the model's risk score:

- **Time since last burn** — "if it hasn't burned in a long time, probably overdue."
- **Controllability / natural firebreaks** — a cell bordered by recently burned
  ground is cheaper and safer to treat.
- **Land ownership** — you need a willing landowner; most Sierra forest is US
  Forest Service land.

These are computed here as *display* signals only. They are deliberately kept
out of the model: the burn/loss history overlaps the training label, so using it
as a feature would leak. Ownership is joined from an optional reference file.

Everything degrades gracefully: if a signal cannot be computed for a cell, the
functions return ``None`` and the dashboard simply omits it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# A neighbor is any cell whose centroid is within this many grid steps.
NEIGHBOR_RADIUS_CELLS = 1.5


def last_detected_burn_year(df: pd.DataFrame) -> dict[Any, int]:
    """Map each grid cell to the most recent year a burn was detected.

    Uses the MODIS ``burned_this_month`` signal across the data window. This is
    not the training label (which is Hansen loss-year based), so it is safe to
    surface. Cells with no detected burn are omitted.
    """
    if "burned_this_month" not in df.columns or "grid_id" not in df.columns:
        return {}
    burned = df.copy()
    burned["burned_this_month"] = pd.to_numeric(burned["burned_this_month"], errors="coerce")
    burned["year"] = pd.to_numeric(burned["year"], errors="coerce")
    burned = burned[burned["burned_this_month"] >= 0.5]
    if burned.empty:
        return {}
    return burned.groupby("grid_id")["year"].max().dropna().astype(int).to_dict()


def years_since_burn(row: pd.Series, burn_years: dict[Any, int]) -> int | None:
    """Years between an observation and the cell's most recent detected burn."""
    grid_id = row.get("grid_id")
    observation_year = pd.to_numeric(row.get("year"), errors="coerce")
    last_year = burn_years.get(grid_id)
    if last_year is None or pd.isna(observation_year):
        return None
    return max(int(observation_year) - int(last_year), 0)


def firebreak_context(
    df: pd.DataFrame,
    row: pd.Series,
    burn_years: dict[Any, int],
    cell_size: float,
) -> dict[str, Any] | None:
    """Summarize recently burned neighbors around a cell (controllability).

    A high share of recently burned neighbors means natural firebreaks — easier
    and cheaper to treat. Returns counts and a plain-English label, or ``None``
    when neighbor geometry is unavailable.
    """
    needed = {"grid_id", "latitude", "longitude"}
    if not needed.issubset(df.columns):
        return None
    try:
        center_lat = float(row["latitude"])
        center_lon = float(row["longitude"])
        observation_year = int(pd.to_numeric(row.get("year"), errors="coerce"))
    except (TypeError, ValueError):
        return None

    cells = df.drop_duplicates("grid_id").copy()
    cells = cells[cells["grid_id"] != row.get("grid_id")]
    reach = cell_size * NEIGHBOR_RADIUS_CELLS
    near = cells[
        (cells["latitude"].sub(center_lat).abs() <= reach)
        & (cells["longitude"].sub(center_lon).abs() <= reach)
    ]
    total = int(len(near))
    if total == 0:
        return {"neighbors": 0, "burned_recently": 0, "share": 0.0, "label": "No mapped neighbors"}

    recent = 0
    for grid_id in near["grid_id"]:
        last_year = burn_years.get(grid_id)
        if last_year is not None and observation_year - int(last_year) <= 5:
            recent += 1
    share = recent / total
    if share >= 0.5:
        label = "Strong natural firebreaks nearby — often easier to treat"
    elif share > 0:
        label = "Some recently burned neighbors — partial firebreaks"
    else:
        label = "No recent burns nearby — fewer natural firebreaks"
    return {"neighbors": total, "burned_recently": recent, "share": share, "label": label}


def load_ownership(config: dict[str, Any] | None, resolver) -> dict[Any, str]:
    """Load an optional grid_id -> ownership map from a reference CSV.

    The file is optional (see ROADMAP Phase 4). Expected columns: ``grid_id`` and
    ``owner``. Returns an empty map when the file is absent or malformed.
    """
    reference = (config or {}).get("paths", {}).get("land_ownership_csv")
    if not reference:
        return {}
    path = resolver(reference)
    if not Path(path).exists():
        return {}
    try:
        owners = pd.read_csv(path)
    except Exception:  # noqa: BLE001 - optional reference, never fatal
        return {}
    if not {"grid_id", "owner"}.issubset(owners.columns):
        return {}
    return dict(zip(owners["grid_id"], owners["owner"].astype(str)))


def priority_summary(
    risk_level: str,
    since_burn: int | None,
    firebreak: dict[str, Any] | None,
    owner: str | None,
) -> str:
    """One plain-English line combining risk with actionability signals."""
    parts: list[str] = []
    if risk_level == "High":
        parts.append("High model risk")
    elif risk_level == "Medium":
        parts.append("Moderate model risk")
    else:
        parts.append("Lower model risk")

    if since_burn is not None and since_burn >= 7:
        parts.append(f"no detected burn in {since_burn}+ years (may be overdue)")
    elif since_burn == 0:
        parts.append("burned within the observation year")
    elif since_burn is not None:
        parts.append(f"burned about {since_burn} year(s) ago")

    if firebreak and firebreak.get("share", 0) >= 0.5:
        parts.append("natural firebreaks make treatment easier")

    if owner:
        parts.append(f"land: {owner}")

    return " · ".join(parts) + "."
