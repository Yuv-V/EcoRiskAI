"""Fire-focused, date-anchored labels and month-before signals.

This module implements two pieces of feedback from the July 2026 TNC check-in:

1. Treat the model as a **fire-risk** model, not a general forest-loss model.
   Timber-harvest loss is driven by land ownership, not ecological stress, and
   mixing it in corrupts the signal. We therefore keep only forest-loss events
   that are associated with a detected burn.

2. Anchor labels to **when** the loss happened, using the Hansen ``lossyear``
   band, and expose the "conditions the month before the burn" idea as
   month-before lag features. On the current sparse export these lag features
   have low coverage, so they are computed and stored but only fed to the model
   when explicitly enabled in config (see ROADMAP Phase 3 — dense extraction).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

# Hansen encodes loss year as a 2-digit offset from 2000 (e.g. 21 -> 2021).
LOSS_YEAR_BASE = 2000

# Environmental signals we track month-over-month for the "month before" idea.
PRIOR_MONTH_SIGNALS = ["ndvi", "ndmi", "nbr", "soil_moisture"]


def decode_loss_year(lossyear: pd.Series) -> pd.Series:
    """Decode the Hansen ``lossyear`` band into a full calendar year.

    ``0`` means "no recorded loss" and stays ``0``; ``21`` becomes ``2021``.
    """
    lossyear = pd.to_numeric(lossyear, errors="coerce").fillna(0).astype(int)
    return np.where(lossyear > 0, LOSS_YEAR_BASE + lossyear, 0)


def build_fire_loss_label(
    df: pd.DataFrame, lookahead_years: int = 1, fire_scoped: bool = True
) -> pd.Series:
    """Build a date-anchored, fire-scoped ``forest loss next year`` label.

    A row is labeled ``1`` when forest loss is recorded ``lookahead_years`` after
    the observation year. When ``fire_scoped`` is true, a loss only counts if the
    location also shows a burn signal, so timber-harvest loss is excluded.

    Returns an integer Series aligned to ``df``'s index.
    """
    loss_year = pd.Series(decode_loss_year(df["lossyear"]), index=df.index)
    observation_year = pd.to_numeric(df["year"], errors="coerce")

    label = (loss_year == observation_year + lookahead_years).astype(int)

    if fire_scoped and "burned_this_month" in df.columns:
        burned = pd.to_numeric(df["burned_this_month"], errors="coerce").fillna(0)
        label = (label & (burned >= 1)).astype(int)

    return label


def add_prior_month_features(
    df: pd.DataFrame, signals: list[str] | None = None
) -> tuple[pd.DataFrame, list[str]]:
    """Add month-before change features for each signal, per grid cell.

    For every signal we compute the change versus the immediately preceding
    monthly observation of the same ``grid_id`` — but only when that prior
    observation is exactly one month earlier. Where no such observation exists
    the value is ``NaN`` (XGBoost handles missing values natively).

    Returns the enriched dataframe and the list of columns that were added.
    """
    signals = signals or PRIOR_MONTH_SIGNALS
    df = df.sort_values(["grid_id", "year", "month"]).copy()

    year = pd.to_numeric(df["year"], errors="coerce")
    month = pd.to_numeric(df["month"], errors="coerce")
    df["_year_month_index"] = year * 12 + month

    grouped = df.groupby("grid_id")
    prior_index = grouped["_year_month_index"].shift(1)
    one_month_back = (df["_year_month_index"] - prior_index) == 1

    added: list[str] = []
    for signal in signals:
        if signal not in df.columns:
            continue
        prior_value = grouped[signal].shift(1)
        delta_column = f"{signal}_delta_1m"
        df[delta_column] = np.where(one_month_back, df[signal] - prior_value, np.nan)
        added.append(delta_column)

    df = df.drop(columns=["_year_month_index"])
    return df, added


def labeling_config(config: dict[str, Any] | None) -> dict[str, Any]:
    """Read labeling options from config with safe MVP defaults."""
    labeling = (config or {}).get("labeling", {})
    return {
        "lookahead_years": int(labeling.get("lookahead_years", 1)),
        "fire_scoped": bool(labeling.get("fire_scoped", True)),
        "use_prior_month_features": bool(labeling.get("use_prior_month_features", False)),
    }
