"""Display helpers that turn raw prediction columns into plain-English labels.

These functions never change the underlying data or CSV format. They only
control how values are shown in the Streamlit dashboard, so non-technical
conservation staff can read the results without a data dictionary.
"""

from __future__ import annotations

import pandas as pd

# Month numbers -> readable names, so "12" reads as "December".
MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

# Raw column name -> human-readable table header.
COLUMN_LABELS = {
    "area_id": "Area ID",
    "grid_id": "Area ID",
    "year": "Year",
    "month": "Month",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "predicted_risk_probability": "Risk Score",
    "predicted_risk_level": "Risk Level",
    "suggested_action": "Suggested Action",
    "ndvi": "Vegetation Health (NDVI)",
    "ndmi": "Moisture Stress (NDMI)",
    "nbr": "Burn/Recovery Signal (NBR)",
    "soil_moisture": "Soil Moisture",
    "precipitation": "Precipitation",
    "temperature_c": "Temperature (°C)",
    "burned_this_month": "Burned This Month",
    "night_lights": "Night Lights",
}

# Short plain-English note shown under each environmental signal.
SIGNAL_EXPLANATIONS = {
    "ndvi": "Vegetation health. Lower values can indicate stressed or sparse vegetation.",
    "ndmi": "Vegetation moisture. Lower values can indicate drier plants and soil.",
    "nbr": "Burn and recovery signal. Useful for spotting fire damage and regrowth.",
    "soil_moisture": "Water available in the soil.",
    "precipitation": "Monthly rainfall and snow-water input.",
    "temperature_c": "Average monthly temperature, in degrees Celsius.",
    "burned_this_month": "Whether fire activity was detected in this area this month.",
    "night_lights": "A rough proxy for human activity and development.",
}

# What each table column means, shown in the "What these columns mean" expander.
COLUMN_EXPLANATIONS = {
    "Area ID": "A friendly label for each location (for example SN-0001).",
    "Year": "The year the measurements are from.",
    "Month": "The month the measurements are from.",
    "Risk Score": "Model-estimated priority score, shown as a percentage. Higher means the area may deserve closer review — it is not a guarantee.",
    "Risk Level": "A simple banding of the risk score: Low, Medium, or High.",
    "Suggested Action": "A plain-language next step suggested by the model.",
    **{COLUMN_LABELS[k]: v for k, v in SIGNAL_EXPLANATIONS.items()},
}

# Columns shown in the risk table, in reading order.
TABLE_COLUMNS = [
    "area_id",
    "year",
    "month",
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

# Environmental signal columns and how many decimals to round each to.
SIGNAL_DECIMALS = {
    "ndvi": 3,
    "ndmi": 3,
    "nbr": 3,
    "soil_moisture": 3,
    "precipitation": 2,
    "temperature_c": 1,
    "night_lights": 2,
}


def add_area_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Add a stable, friendly ``area_id`` (SN-0001 style) for each location.

    One physical location can appear in several months and years, so the ID is
    keyed to ``grid_id`` and stays the same across time steps. Areas are ordered
    north-to-south then west-to-east so the numbering roughly follows the map.
    The original ``grid_id`` is preserved untouched.
    """
    df = df.copy()
    if "grid_id" not in df.columns:
        df["original_grid_id"] = range(len(df))
        df["area_id"] = [f"SN-{i + 1:04d}" for i in range(len(df))]
        return df

    # Preserve the raw grid id under a clearly-internal name.
    df["original_grid_id"] = df["grid_id"]

    # One SN id per unique grid_id, ordered north-to-south then west-to-east so
    # the numbering roughly follows the map. Repeated grid_ids (same location in
    # different months/years) always resolve to the same SN id.
    location_order = (
        df[["grid_id", "latitude", "longitude"]]
        .drop_duplicates("grid_id")
        .sort_values(["latitude", "longitude"], ascending=[False, True])
        .reset_index(drop=True)
    )
    id_map = {
        grid_id: f"SN-{i + 1:04d}"
        for i, grid_id in enumerate(location_order["grid_id"])
    }
    df["area_id"] = df["grid_id"].map(id_map)
    return df


def month_label(month: object) -> str:
    """Return a readable month name, tolerating floats and missing values."""
    try:
        return MONTH_NAMES.get(int(float(month)), str(month))
    except (TypeError, ValueError):
        return str(month)


def format_risk_score(probability: float) -> str:
    """Format a 0-1 probability as a percentage string."""
    try:
        return f"{float(probability) * 100:.0f}%"
    except (TypeError, ValueError):
        return "—"


def sorted_int_options(series: pd.Series) -> list[int]:
    """Return sorted, unique integer options from a column for filter menus."""
    values = pd.to_numeric(series, errors="coerce").dropna().astype(int).unique()
    return sorted(int(v) for v in values)


# --- Environmental signal interpretation (MVP, rough ranges) --------------

# Fixed thresholds for index-style signals: (upper_bound, label). The last
# entry uses float("inf") to catch everything above the previous bound.
FIXED_SCALES = {
    "ndvi": [
        (0.20, "Very Low"),
        (0.40, "Stressed"),
        (0.60, "Moderate"),
        (float("inf"), "Healthy"),
    ],
    "ndmi": [
        (0.00, "Very Dry"),
        (0.20, "Dry"),
        (0.40, "Moderate"),
        (float("inf"), "Moist"),
    ],
    "nbr": [
        (0.10, "Disturbed"),
        (0.30, "Low Recovery"),
        (0.50, "Moderate"),
        (float("inf"), "Strong"),
    ],
}

# Tercile-based signals: labels for the bottom, middle, and top third of the
# current dataset.
TERCILE_LABELS = {
    "soil_moisture": ("Low", "Moderate", "High"),
    "precipitation": ("Low", "Moderate", "High"),
    "temperature_c": ("Cool", "Moderate", "Hot"),
    "night_lights": ("Low Human Signal", "Moderate", "Higher Human Signal"),
}

# Human-readable scale text shown in the "how to interpret" expander.
SCALE_DESCRIPTIONS = {
    "ndvi": "Below 0.20 Very Low · 0.20–0.40 Stressed · 0.40–0.60 Moderate · above 0.60 Healthy",
    "ndmi": "Below 0.00 Very Dry · 0.00–0.20 Dry · 0.20–0.40 Moderate · above 0.40 Moist",
    "nbr": "Below 0.10 Disturbed · 0.10–0.30 Low Recovery · 0.30–0.50 Moderate · above 0.50 Strong",
    "soil_moisture": "Relative to this dataset: bottom third Low · middle third Moderate · top third High",
    "precipitation": "Relative to this dataset: bottom third Low · middle third Moderate · top third High",
    "temperature_c": "Relative to this dataset: bottom third Cool · middle third Moderate · top third Hot",
    "night_lights": "Relative to this dataset: bottom third Low Human Signal · middle third Moderate · top third Higher Human Signal",
    "burned_this_month": "Yes if fire activity was detected in this area this month, otherwise No.",
}


def compute_terciles(df: pd.DataFrame) -> dict[str, tuple[float, float]]:
    """Return (lower, upper) tercile cut points for each tercile-based signal."""
    cuts: dict[str, tuple[float, float]] = {}
    for column in TERCILE_LABELS:
        if column not in df.columns:
            continue
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if values.empty:
            continue
        cuts[column] = (float(values.quantile(1 / 3)), float(values.quantile(2 / 3)))
    return cuts


def interpret_signal(
    column: str, value: object, terciles: dict[str, tuple[float, float]] | None = None
) -> str:
    """Return a short plain-English interpretation label for a signal value.

    Index-style signals (NDVI, NDMI, NBR) use fixed thresholds. Dataset-relative
    signals (soil moisture, precipitation, temperature, night lights) use the
    supplied tercile cut points. Returns an empty string if not interpretable.
    """
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ""

    if column in FIXED_SCALES:
        for upper, label in FIXED_SCALES[column]:
            if numeric < upper:
                return label
        return FIXED_SCALES[column][-1][1]

    if column in TERCILE_LABELS and terciles and column in terciles:
        low, high = terciles[column]
        labels = TERCILE_LABELS[column]
        if numeric <= low:
            return labels[0]
        if numeric <= high:
            return labels[1]
        return labels[2]

    return ""


def signal_display(
    column: str, value: object, terciles: dict[str, tuple[float, float]] | None = None
) -> str:
    """Format a signal for the UI table as ``value — interpretation``.

    Example: ``0.061 — Very Low``. Falls back to the bare rounded value when no
    interpretation applies. Display-only; raw numeric columns stay untouched.
    """
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "—"
    decimals = SIGNAL_DECIMALS.get(column, 3)
    shown = f"{numeric:.{decimals}f}"
    label = interpret_signal(column, numeric, terciles)
    return f"{shown} — {label}" if label else shown
