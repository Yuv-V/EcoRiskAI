"""Streamlit dashboard for the EcoRiskAI MVP.

A conservation prioritization prototype for Sierra Nevada / California forest
ecosystems. The dashboard surfaces areas that may deserve closer review; it does
not replace field experts.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.features.prioritization import (
    firebreak_context,
    last_detected_burn_year,
    load_ownership,
    priority_summary,
    years_since_burn,
)
from src.utils.config import load_config, resolve_project_path
from src.utils.display import (
    COLUMN_EXPLANATIONS,
    COLUMN_LABELS,
    SCALE_DESCRIPTIONS,
    SIGNAL_DECIMALS,
    SIGNAL_EXPLANATIONS,
    TABLE_COLUMNS,
    add_area_ids,
    compute_terciles,
    format_risk_score,
    interpret_signal,
    month_label,
    signal_display,
    sorted_int_options,
)

# Risk colors used consistently across the map, legend, and badges.
RISK_COLORS = {
    "Low": [46, 125, 79],     # forest green
    "Medium": [224, 138, 43],  # amber
    "High": [192, 57, 43],     # clay red
}
RISK_HEX = {
    "Low": "#2E7D4F",
    "Medium": "#E08A2B",
    "High": "#C0392B",
}

# Default view: California / Sierra Nevada, not the whole world.
DEFAULT_LATITUDE = 37.6
DEFAULT_LONGITUDE = -119.4
DEFAULT_ZOOM = 6.2

# Study-area grid spacing (degrees). Cells are drawn at this size so predictions
# read as a filled risk *surface* rather than floating points; as full-landscape
# coverage fills in (Phase 3), the cells tile into a continuous Sierra-wide map.
CELL_SIZE_DEG = 0.017966


def inject_theme() -> None:
    """Apply a calm, conservation-focused visual theme via CSS."""
    st.markdown(
        """
        <style>
        :root {
            --forest: #2E7D32;
            --forest-deep: #1B5E20;
            --sage: #E8F5E9;
            --card: #FBFDFB;
            --border: #A5D6A7;
            --border-soft: #C8E6C9;
            --bark: #5D6B54;
            --ink: #1F2A24;
        }
        .block-container { padding-top: 2.2rem; max-width: 1400px; }
        h1, h2, h3 { color: var(--forest-deep); letter-spacing: -0.01em; }
        h1 { font-weight: 700; }

        /* Header band with subtle nature gradient */
        .eco-header {
            background: linear-gradient(100deg, #E8F5E9 0%, #F1F8E9 55%, #FFFFFF 100%);
            border: 1px solid var(--border);
            border-left: 5px solid var(--forest);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.9rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .eco-header .eco-title { font-size: 2rem; font-weight: 700; color: var(--forest-deep); }
        .eco-header .eco-sub { color: var(--bark); font-size: 1rem; margin-top: 0.15rem; }
        .eco-badge {
            display: inline-flex; align-items: center; gap: 0.4rem;
            background: var(--forest); color: #fff;
            padding: 0.4rem 0.9rem; border-radius: 999px;
            font-size: 0.82rem; font-weight: 600; white-space: nowrap;
        }

        /* Green section headers */
        .eco-section {
            display: flex; align-items: center; gap: 0.5rem;
            background: linear-gradient(90deg, #E8F5E9 0%, rgba(232,245,233,0) 90%);
            border-left: 4px solid var(--forest);
            border-radius: 6px;
            padding: 0.45rem 0.75rem;
            margin: 0.2rem 0 0.6rem 0;
        }
        .eco-section .eco-section-title { color: var(--forest-deep); font-weight: 700; font-size: 1.2rem; }
        .eco-note {
            background: #E8F5E9; border: 1px solid #A5D6A7; border-radius: 8px;
            padding: 0.6rem 0.8rem; color: #33691E; font-size: 0.85rem; line-height: 1.5;
            margin-top: 0.7rem;
        }

        /* Cards */
        .eco-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-top: 3px solid var(--forest);
            border-radius: 12px;
            padding: 1.1rem 1.25rem;
        }
        .eco-card h4 { color: var(--forest-deep); margin: 0 0 0.5rem 0; font-size: 1.05rem; }
        .eco-card p, .eco-card li { color: var(--ink); font-size: 0.9rem; line-height: 1.5; }

        /* Metric cards */
        div[data-testid="stMetric"] {
            background: var(--card);
            border: 1px solid var(--border-soft);
            border-left: 4px solid var(--forest);
            border-radius: 12px;
            padding: 0.9rem 1rem;
        }
        div[data-testid="stMetricValue"] { color: var(--forest-deep); font-weight: 700; }
        div[data-testid="stMetricLabel"] { color: var(--bark); }

        /* Sidebar */
        section[data-testid="stSidebar"] { background: var(--sage); border-right: 1px solid var(--border); }
        section[data-testid="stSidebar"] h2 { font-size: 1.15rem; }

        /* Legend swatches */
        .legend-row { display: flex; align-items: center; gap: 0.55rem; margin: 0.3rem 0; }
        .legend-dot { width: 14px; height: 14px; border-radius: 50%; border: 1px solid rgba(0,0,0,0.15); flex: none; }
        .legend-text { font-size: 0.9rem; color: var(--ink); }

        /* Risk badge */
        .risk-badge {
            display: inline-block; padding: 0.15rem 0.7rem; border-radius: 999px;
            color: #fff; font-weight: 600; font-size: 0.85rem;
        }
        .signal-note { color: var(--bark); font-size: 0.82rem; margin: 0 0 0.7rem 0; }
        .signal-value { color: var(--ink); font-size: 1.05rem; font-weight: 600; }
        .signal-label { color: var(--forest-deep); font-weight: 600; font-size: 0.9rem; }
        hr { border-color: var(--border); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def pending_map_click(area_options: list[str]) -> str | None:
    """Return the area clicked on the map, read from the chart's widget state."""
    state = st.session_state.get("risk_map")
    if not state:
        return None
    try:
        objects = state.selection.objects
    except AttributeError:
        return None
    for items in dict(objects).values():
        for obj in items:
            area = (obj or {}).get("area_id")
            if area in area_options:
                return area
    return None


def pending_table_click(
    display_table: pd.DataFrame, area_options: list[str]
) -> str | None:
    """Return the area of the clicked table row, read from widget state."""
    state = st.session_state.get("risk_table")
    if not state:
        return None
    try:
        rows = state.selection.rows
    except AttributeError:
        return None
    if not rows:
        return None
    index = rows[0]
    if not 0 <= index < len(display_table):
        return None
    area = display_table.iloc[index]["Area ID"]
    return area if area in area_options else None


def apply_pending_selections(display_table: pd.DataFrame, area_options: list[str]) -> None:
    """Sync map/table clicks into the area selectbox state.

    Must run before the selectbox is instantiated. Each click source is applied
    only once (tracked via a marker key) so a stale selection does not keep
    overriding the dropdown.
    """
    for source, area in (
        ("map", pending_map_click(area_options)),
        ("table", pending_table_click(display_table, area_options)),
    ):
        marker = f"_last_{source}_click"
        if area and area != st.session_state.get(marker):
            st.session_state[marker] = area
            st.session_state["area_select"] = area


def section_header(icon: str, title: str) -> None:
    """Render a soft green section header with a small leaf/terrain icon."""
    st.markdown(
        f'<div class="eco-section"><span style="font-size:1.15rem">{icon}</span>'
        f'<span class="eco-section-title">{title}</span></div>',
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_predictions() -> tuple[pd.DataFrame, bool] | None:
    """Load predictions with friendly area IDs.

    Prefers the full-landscape (wall-to-wall) predictions when present, so the
    map fills in automatically after a dense extraction. Returns the dataframe
    and a flag for whether the wall-to-wall output was used.
    """
    config = load_config()
    landscape_key = config["paths"].get("landscape_predictions_csv")
    if landscape_key:
        landscape_path = resolve_project_path(landscape_key)
        if landscape_path.exists():
            return add_area_ids(pd.read_csv(landscape_path)), True

    predictions_path = resolve_project_path(config["paths"]["predictions_csv"])
    if not predictions_path.exists():
        return None
    return add_area_ids(pd.read_csv(predictions_path)), False


@st.cache_data(show_spinner=False)
def load_ownership_map() -> dict:
    """Load the optional grid_id -> owner reference (empty when absent)."""
    return load_ownership(load_config(), resolve_project_path)


def show_prioritization(full_df: pd.DataFrame, selected_row: pd.Series) -> None:
    """Show conservation prioritization context for the selected cell.

    These are decision-support signals (time since last burn, natural firebreaks,
    land ownership) — separate from the model risk score, mirroring how experts
    decide where to act. Signals that cannot be computed are simply omitted.
    """
    burn_years = last_detected_burn_year(full_df)
    since_burn = years_since_burn(selected_row, burn_years)
    firebreak = firebreak_context(full_df, selected_row, burn_years, CELL_SIZE_DEG)
    owner = load_ownership_map().get(selected_row.get("grid_id"))
    level = selected_row["predicted_risk_level"]

    rows = []
    if since_burn is not None:
        if since_burn >= 7:
            value = f"~{since_burn} years — may be overdue for treatment"
        elif since_burn == 0:
            value = "Burned within the observation year"
        else:
            value = f"~{since_burn} year(s)"
        rows.append(("🔥 Time since last detected burn", value))
    else:
        rows.append(("🔥 Time since last detected burn", "No burn detected in the data window"))
    if firebreak is not None:
        rows.append(
            ("🧭 Controllability (natural firebreaks)",
             f"{firebreak['burned_recently']} of {firebreak['neighbors']} neighboring cells "
             f"burned recently — {firebreak['label']}")
        )
    rows.append(("🗂️ Land ownership", owner if owner else "Not available (add a reference file)"))

    body = "".join(
        f'<div style="margin-bottom:0.5rem"><div class="signal-label">{label}</div>'
        f'<div class="signal-value" style="font-size:0.95rem">{value}</div></div>'
        for label, value in rows
    )
    summary = priority_summary(level, since_burn, firebreak, owner)
    st.markdown(
        f"""
        <div class="eco-card">
            <h4>🧭 Conservation prioritization context</h4>
            <p class="signal-note" style="margin-top:-0.2rem">
            Decision-support signals for where to act — separate from the model risk score.</p>
            {body}
            <div class="eco-note"><b>In short:</b> {summary}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render the left filter panel and return the filtered dataframe.

    Filter options always come from the sorted, unique values in the dataset, so
    any year (e.g. 2026) or month (e.g. 12) present in the CSV shows up.
    """
    st.sidebar.markdown("## Filters")

    if st.sidebar.button("Reset filters", width="stretch"):
        for key in (
            "f_years", "f_months", "f_risks", "f_min_score",
            "area_select", "_last_map_click", "_last_table_click",
        ):
            st.session_state.pop(key, None)
        st.rerun()

    years = sorted_int_options(df["year"])
    months = sorted_int_options(df["month"])
    present_levels = [lvl for lvl in ("Low", "Medium", "High") if lvl in set(df["predicted_risk_level"])]

    st.sidebar.markdown("**Year**")
    selected_years = st.sidebar.multiselect(
        "Year", years, default=years, key="f_years", label_visibility="collapsed"
    )
    st.sidebar.caption("Which years of predictions to include.")

    st.sidebar.markdown("**Month**")
    selected_month_labels = st.sidebar.multiselect(
        "Month",
        options=[month_label(m) for m in months],
        default=[month_label(m) for m in months],
        key="f_months",
        label_visibility="collapsed",
    )
    st.sidebar.caption("Which months to include.")
    label_to_month = {month_label(m): m for m in months}
    selected_months = [label_to_month[lbl] for lbl in selected_month_labels]

    st.sidebar.markdown("**Risk Level**")
    selected_risks = st.sidebar.multiselect(
        "Risk Level", present_levels, default=present_levels, key="f_risks",
        label_visibility="collapsed",
    )
    st.sidebar.caption("Low, Medium, or High risk banding.")

    st.sidebar.markdown("**Minimum Risk Score**")
    min_score = st.sidebar.slider(
        "Minimum Risk Score", 0, 100, 0, key="f_min_score", format="%d%%",
        label_visibility="collapsed",
    )
    st.sidebar.caption("Hide areas below this model priority score.")

    year_col = pd.to_numeric(df["year"], errors="coerce")
    month_col = pd.to_numeric(df["month"], errors="coerce")
    score_col = pd.to_numeric(df["predicted_risk_probability"], errors="coerce") * 100

    return df[
        year_col.isin(selected_years)
        & month_col.isin(selected_months)
        & df["predicted_risk_level"].isin(selected_risks)
        & (score_col >= min_score)
    ].copy()


def show_analytics(df: pd.DataFrame) -> None:
    """Render simple risk summary metrics."""
    total = len(df)
    average = df["predicted_risk_probability"].mean() if total else 0
    high = int((df["predicted_risk_level"] == "High").sum())
    medium = int((df["predicted_risk_level"] == "Medium").sum())
    low = int((df["predicted_risk_level"] == "Low").sum())

    cols = st.columns(5)
    cols[0].metric("Areas shown", f"{total:,}")
    cols[1].metric("Average risk score", format_risk_score(average))
    cols[2].metric("High risk", f"{high:,}")
    cols[3].metric("Medium risk", f"{medium:,}")
    cols[4].metric("Low risk", f"{low:,}")


@st.cache_data(show_spinner=False)
def load_metrics() -> dict | None:
    """Load the saved model metrics JSON, if present."""
    config = load_config()
    metrics_path = resolve_project_path(config["paths"].get("metrics_path", ""))
    if not metrics_path or not Path(metrics_path).exists():
        return None
    try:
        return json.loads(Path(metrics_path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def show_top_priorities(df: pd.DataFrame) -> None:
    """Highlight the highest-risk areas — the 'where to look first' view."""
    if df.empty:
        return
    top = df.sort_values("predicted_risk_probability", ascending=False).head(5)
    items = ""
    for _, row in top.iterrows():
        level = row["predicted_risk_level"]
        items += (
            f'<div style="display:flex; align-items:center; gap:0.6rem; padding:0.4rem 0; '
            f'border-bottom:1px solid var(--border-soft)">'
            f'<span style="width:9px; height:9px; border-radius:50%; background:{RISK_HEX.get(level, "#6B5D4F")}; flex:none"></span>'
            f'<span style="font-weight:700; color:var(--forest-deep); min-width:74px">{row["area_id"]}</span>'
            f'<span style="font-weight:700; min-width:52px">{format_risk_score(row["predicted_risk_probability"])}</span>'
            f'<span class="signal-note" style="flex:1">{row["latitude"]:.3f}, {row["longitude"]:.3f}'
            f' · {month_label(row["month"])} {int(row["year"])}</span></div>'
        )
    st.markdown(
        f"""
        <div class="eco-card">
            <h4>⭐ Top areas to review first</h4>
            <p class="signal-note" style="margin-top:-0.2rem">
            Highest model risk in the current filters — a starting point for closer review.</p>
            {items}
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_model_performance_card() -> None:
    """Show honest model performance metrics as a card, for reviewer trust."""
    metrics = load_metrics()
    if not metrics:
        return

    if not metrics.get("trained"):
        st.markdown(
            """
            <div class="eco-card">
                <h4>📈 Model performance</h4>
                <p class="signal-note" style="margin-top:-0.2rem">
                Currently showing a transparent heuristic risk score — the XGBoost model
                was not trained on the last run. Metrics appear here once it trains.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    def pct(value: object) -> str:
        try:
            return f"{float(value) * 100:.0f}%"
        except (TypeError, ValueError):
            return "—"

    stats = [
        ("ROC-AUC", pct(metrics.get("roc_auc")), "ranking quality (50% = coin flip)"),
        ("Accuracy", pct(metrics.get("accuracy")), "overall correct"),
        ("Recall", pct(metrics.get("recall")), "high-risk areas caught"),
        ("Precision", pct(metrics.get("precision")), "of flagged, truly high-risk"),
    ]
    tiles = "".join(
        f'<div style="flex:1; min-width:96px">'
        f'<div style="font-size:1.4rem; font-weight:700; color:var(--forest-deep)">{value}</div>'
        f'<div class="signal-label">{label}</div>'
        f'<div class="signal-note">{note}</div></div>'
        for label, value, note in stats
    )
    st.markdown(
        f"""
        <div class="eco-card">
            <h4>📈 Model performance</h4>
            <div style="display:flex; gap:1rem; flex-wrap:wrap">{tiles}</div>
            <div class="eco-note">
            Trained on {int(metrics.get('training_rows', 0)):,} rows
            ({metrics.get('positive_labels', 0)} at-risk / {metrics.get('negative_labels', 0)} not),
            {metrics.get('n_features', 0)} features. Early MVP numbers — directional, not validated.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Friendly names for model features that aren't in COLUMN_LABELS.
_FEATURE_NAMES = {
    "blue": "Blue reflectance", "green": "Green reflectance", "red": "Red reflectance",
    "nir": "Near-infrared", "swir1": "Shortwave IR 1", "swir2": "Shortwave IR 2",
    "treecover2000": "Tree cover (2000)", "elevation": "Elevation", "slope": "Slope",
    "aspect": "Aspect", "landsat_image_count": "Image count",
    "ndvi_delta_1m": "Vegetation change (1mo)", "ndmi_delta_1m": "Moisture change (1mo)",
    "nbr_delta_1m": "Burn signal change (1mo)", "soil_moisture_delta_1m": "Soil moisture change (1mo)",
}


def _feature_name(raw: str) -> str:
    """Human-readable label for a model feature."""
    return COLUMN_LABELS.get(raw) or _FEATURE_NAMES.get(raw, raw.replace("_", " ").title())


def show_feature_importance() -> None:
    """Bar chart of what drives the model's risk score (from saved metrics)."""
    metrics = load_metrics()
    importances = (metrics or {}).get("feature_importances") if metrics else None
    if not importances:
        return
    ranked = sorted(importances.items(), key=lambda kv: kv[1], reverse=True)[:8]
    top = max((v for _, v in ranked), default=1) or 1
    bars = ""
    for raw, value in ranked:
        width = max(value / top * 100, 2)
        bars += (
            '<div style="display:flex; align-items:center; gap:0.6rem; margin:0.35rem 0">'
            f'<span style="width:150px; font-size:0.82rem; color:var(--ink); text-align:right; flex:none">{_feature_name(raw)}</span>'
            f'<span style="flex:1; background:var(--sage); border-radius:4px; overflow:hidden">'
            f'<span style="display:block; width:{width:.0f}%; height:14px; background:var(--forest)"></span></span>'
            f'<span style="width:44px; font-size:0.8rem; color:var(--bark)">{value*100:.0f}%</span></div>'
        )
    st.markdown(
        f"""
        <div class="eco-card">
            <h4>🔍 What drives the risk score</h4>
            <p class="signal-note" style="margin-top:-0.2rem">
            Relative influence of each signal on the model. Reflectance and heat rank
            high — a reminder that spectral signals can partly reflect a burn that
            already happened (see limitations).</p>
            {bars}
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_risk_trend(full_df: pd.DataFrame, selected_row: pd.Series) -> None:
    """Line chart of the selected area's risk score over time."""
    area = selected_row.get("area_id")
    records = full_df[full_df["area_id"] == area].copy()
    if records.empty:
        return
    records["period_index"] = (
        pd.to_numeric(records["year"], errors="coerce") * 12
        + pd.to_numeric(records["month"], errors="coerce")
    )
    records = records.dropna(subset=["period_index"]).sort_values("period_index")
    if len(records) < 2:
        st.caption("Only one time point available for this area — no trend to plot yet.")
        return
    records["Period"] = [
        f"{month_label(m)[:3]} {int(y)}"
        for m, y in zip(records["month"], records["year"])
    ]
    records["Risk score (%)"] = (
        pd.to_numeric(records["predicted_risk_probability"], errors="coerce") * 100
    ).round(0)
    st.markdown("##### Risk over time")
    st.line_chart(records.set_index("Period")["Risk score (%)"], height=180)


def _cell_polygon(longitude: float, latitude: float, size: float = CELL_SIZE_DEG) -> list[list[float]]:
    """Return a square cell polygon (lon/lat corners) centered on a point."""
    half = size / 2
    return [
        [longitude - half, latitude - half],
        [longitude + half, latitude - half],
        [longitude + half, latitude + half],
        [longitude - half, latitude + half],
    ]


def show_map(df: pd.DataFrame, selected_row: pd.Series | None) -> None:
    """Render the Sierra Nevada risk as a filled per-cell surface.

    Each prediction is drawn as a grid cell (not a floating point), so the map
    reads as a continuous risk surface. Exactly one cell (``selected_row``) is
    highlighted, so a chosen area for a given year/month never lights up
    multiple mixed cells.
    """
    if df.empty:
        st.info("No areas match the selected filters. Try resetting the filters.")
        return

    map_df = df.copy()
    map_df["color"] = map_df["predicted_risk_level"].map(RISK_COLORS)
    map_df["risk_pct"] = (
        pd.to_numeric(map_df["predicted_risk_probability"], errors="coerce") * 100
    ).round(0)
    map_df["polygon"] = [
        _cell_polygon(lon, lat)
        for lon, lat in zip(map_df["longitude"], map_df["latitude"])
    ]

    has_selection = selected_row is not None
    # Dim the field a little when one cell is spotlighted.
    base_alpha = 115 if has_selection else 200
    map_df["fill"] = map_df["color"].map(lambda c: list(c) + [base_alpha])

    try:
        import pydeck as pdk

        view_state = pdk.ViewState(
            latitude=DEFAULT_LATITUDE,
            longitude=DEFAULT_LONGITUDE,
            zoom=DEFAULT_ZOOM,
            pitch=0,
        )
        base_layer = pdk.Layer(
            "PolygonLayer",
            id="risk-cells",
            data=map_df,
            get_polygon="polygon",
            get_fill_color="fill",
            get_line_color=[255, 255, 255, 90],
            line_width_min_pixels=0.5,
            stroked=True,
            filled=True,
            pickable=True,
        )
        layers = [base_layer]

        if has_selection:
            selected_df = pd.DataFrame([{
                "polygon": _cell_polygon(
                    float(selected_row["longitude"]), float(selected_row["latitude"])
                ),
                "fill": list(RISK_COLORS.get(selected_row["predicted_risk_level"], [107, 93, 79])) + [255],
                "area_id": selected_row["area_id"],
                "predicted_risk_level": selected_row["predicted_risk_level"],
                "risk_pct": round(float(selected_row["predicted_risk_probability"]) * 100),
            }])
            highlight = pdk.Layer(
                "PolygonLayer",
                id="risk-selected",
                data=selected_df,
                get_polygon="polygon",
                get_fill_color="fill",
                get_line_color=[18, 63, 40],
                line_width_min_pixels=3,
                stroked=True,
                filled=True,
                pickable=True,
            )
            layers.append(highlight)

        tooltip = {
            "html": (
                "<b>Area:</b> {area_id}<br/>"
                "<b>Risk level:</b> {predicted_risk_level}<br/>"
                "<b>Risk score:</b> {risk_pct}%"
            ),
            "style": {"backgroundColor": "#123F28", "color": "#fff"},
        }
        st.pydeck_chart(
            pdk.Deck(
                map_style="light",
                layers=layers,
                initial_view_state=view_state,
                tooltip=tooltip,
            ),
            on_select="rerun",
            selection_mode="single-object",
            key="risk_map",
        )
        st.caption("Each square is one grid cell. Click a cell to select that area.")
    except ModuleNotFoundError:
        st.map(map_df.rename(columns={"latitude": "lat", "longitude": "lon"}))


def show_map_key(df: pd.DataFrame) -> None:
    """Render the plain-English 'How to Read This Map' card."""
    counts = df["predicted_risk_level"].value_counts().to_dict()
    legend = (
        ("Low", "<b>Green</b> — Low relative ecosystem risk"),
        ("Medium", "<b>Orange</b> — Medium relative ecosystem risk"),
        ("High", "<b>Red</b> — High relative ecosystem risk"),
    )
    rows = ""
    for level, label in legend:
        count = int(counts.get(level, 0))
        empty = (
            '<div class="signal-note" style="margin:0 0 0.2rem 22px">'
            "0 cells currently fall into this range.</div>"
            if count == 0
            else ""
        )
        rows += (
            f'<div class="legend-row">'
            f'<span class="legend-dot" style="background:{RISK_HEX[level]}"></span>'
            f'<span class="legend-text">{label} · {count} cells</span></div>{empty}'
        )
    medium_note = ""
    if int(counts.get("Medium", 0)) == 0:
        medium_note = (
            '<div class="eco-note">Medium risk may be empty because this early model '
            "currently separates most areas into low or high risk. More training data "
            "should improve balance.</div>"
        )
    st.markdown(
        f"""
        <div class="eco-card">
            <h4>🍃 How to read this map</h4>
            {rows}
            <p style="margin-top:0.7rem">
            <b>Risk Score</b> is a model-estimated priority score — not a guarantee.
            Higher risk means the location may deserve closer review or monitoring.
            </p>
            <div class="eco-note">
            Risk is relative within this MVP dataset. It should be used to prioritize
            review, not as a final ecological diagnosis.
            </div>
            {medium_note}
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_signal_glossary() -> None:
    """Plain-English 'Signal Key' with interpretation scales for each variable."""
    with st.expander("How to interpret environmental signals"):
        for raw, note in SIGNAL_EXPLANATIONS.items():
            st.markdown(f"**{COLUMN_LABELS[raw]}** — {note}")
            scale = SCALE_DESCRIPTIONS.get(raw)
            if scale:
                st.caption(scale)


def build_display_table(
    df: pd.DataFrame, terciles: dict[str, tuple[float, float]]
) -> pd.DataFrame:
    """Return a renamed, reader-friendly copy of the risk table.

    Environmental signals render as ``value — interpretation`` strings (for
    example ``0.061 — Very Low``). This is a display copy only; the source
    dataframe keeps its raw numeric columns for filtering and the model.
    """
    table = df[TABLE_COLUMNS].copy()
    table = table.sort_values("predicted_risk_probability", ascending=False).reset_index(drop=True)

    table["month"] = table["month"].map(month_label)
    table["predicted_risk_probability"] = (
        pd.to_numeric(table["predicted_risk_probability"], errors="coerce") * 100
    ).round(0)
    for raw in SIGNAL_DECIMALS:
        table[raw] = table[raw].map(lambda v, c=raw: signal_display(c, v, terciles))
    table["burned_this_month"] = table["burned_this_month"].map(
        lambda v: "Yes" if float(v) >= 0.5 else "No"
    )
    table["year"] = pd.to_numeric(table["year"], errors="coerce").astype("Int64")

    return table.rename(columns=COLUMN_LABELS)


def show_table(display_table: pd.DataFrame) -> None:
    """Render the risk table with readable headers, row selection, and a column explainer."""
    st.dataframe(
        display_table,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="risk_table",
        column_config={
            "Risk Score": st.column_config.NumberColumn(
                "Risk Score", format="%d%%", width="small"
            ),
            "Suggested Action": st.column_config.TextColumn(
                "Suggested Action", width="large"
            ),
            "Latitude": None,
            "Longitude": None,
        },
    )
    st.caption("Click a row to select that area.")
    with st.expander("What these columns mean"):
        for label, note in COLUMN_EXPLANATIONS.items():
            st.markdown(f"**{label}** — {note}")


def show_selected_details(
    row: pd.Series, terciles: dict[str, tuple[float, float]]
) -> None:
    """Show plain-English details for a single selected record."""
    level = row["predicted_risk_level"]
    st.markdown(
        f"""
        <div class="eco-card">
            <div style="display:flex; align-items:center; gap:0.8rem; flex-wrap:wrap;">
                <span style="font-size:1.35rem; font-weight:700; color:var(--forest-deep)">
                    {row['area_id']}</span>
                <span class="risk-badge" style="background:{RISK_HEX.get(level, '#6B5D4F')}">
                    {level} risk</span>
                <span style="color:var(--bark)">Risk Score:
                    <b>{format_risk_score(row['predicted_risk_probability'])}</b></span>
            </div>
            <p style="margin:0.6rem 0 0.2rem 0"><b>Suggested action:</b> {row['suggested_action']}</p>
            <p style="margin:0.15rem 0"><b>Location:</b> {row['latitude']:.4f}, {row['longitude']:.4f}
                &nbsp;·&nbsp; <b>Period:</b> {month_label(row['month'])} {int(row['year'])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### Key environmental signals")
    signals = list(SIGNAL_EXPLANATIONS.keys())
    columns = st.columns(2)
    for i, raw in enumerate(signals):
        value = row[raw]
        if raw == "burned_this_month":
            shown = "Yes" if float(value) >= 0.5 else "No"
            interpretation = ""
        else:
            shown = f"{float(value):.{SIGNAL_DECIMALS.get(raw, 3)}f}"
            interpretation = interpret_signal(raw, value, terciles)
        reading = f" — {interpretation}" if interpretation else ""
        columns[i % 2].markdown(
            f'<div style="margin-bottom:0.7rem">'
            f'<div class="signal-label">{COLUMN_LABELS[raw]}: '
            f'<span class="signal-value">{shown}</span>'
            f'<span class="signal-note" style="margin-left:0.3rem">{reading}</span></div>'
            f'<div class="signal-note">{SIGNAL_EXPLANATIONS[raw]}</div></div>',
            unsafe_allow_html=True,
        )


def show_methodology() -> None:
    """Expanded methodology and purpose section."""
    section_header("📖", "Methodology & purpose")
    with st.expander("Purpose, data sources, model, and limitations", expanded=False):
        st.markdown(
            """
**Purpose.** EcoRiskAI is a prototype conservation prioritization tool. It does
not replace field experts — it helps surface areas that may deserve closer review.

**Study area.** Sierra Nevada / California forest ecosystems.

**Data sources.**
- **Landsat 8/9** — satellite reflectance and vegetation signals
- **Hansen Global Forest Change** — historical forest-loss labels
- **SRTM** — elevation, slope, aspect
- **SMAP** — soil moisture
- **GPM** — precipitation
- **ERA5-Land** — temperature
- **MODIS Burned Area** — fire disturbance
- **VIIRS Night Lights** — human activity / development proxy

**Calculated indicators.**
- **NDVI** — vegetation health
- **NDMI** — moisture stress
- **NBR** — burn / recovery signal
- Terrain variables from SRTM
- Monthly climate-stress variables

**Model.**
- Baseline XGBoost classifier
- **Fire-focused:** the target is forest loss that is associated with a burn, so
  timber-harvest loss (driven by land ownership, not ecological stress) is
  excluded and does not blur the wildfire signal.
- **Date-anchored labels:** loss events are tied to the Hansen loss year, and a
  location counts as risky when loss is recorded the following year.
- **No concurrent-burn shortcut:** the "burned this month" flag is shown for
  context but is **not** a model input, so the model learns pre-burn conditions
  instead of simply detecting that a fire already happened.
- Outputs a relative ecosystem-risk probability. Intended as an **annually
  updated** product, not a live monthly feed.

**Known limitations (and what we're improving).**
- This is an MVP prototype; the risk score is a relative priority, not a guarantee.
- **Sampled, not wall-to-wall.** Predictions currently cover a sample of grid
  cells rather than every cell in the Sierra Nevada. A full-landscape risk
  surface is the top priority for the next version.
- **Limited time depth.** The model reads mostly single-month snapshots. It does
  not yet capture lag effects — for example wet years building fuel that a later
  drought turns to tinder. "Month before" features are built into the pipeline
  and switch on once denser data is available.
- Some spectral signals can partly reflect a burn that already occurred; cleaner
  pre-event conditioning needs denser monthly extraction.
- Forest loss is only one proxy for ecosystem degradation, and field expertise
  is still required.

**Prioritization signals (decision support, new).**
Alongside the model risk score, each area now shows factors experts use to decide
*where to act*: time since the last detected burn (overdue areas), natural
firebreaks / controllability from neighboring burn history, and land ownership
(when a reference file is provided). These are shown for context and are kept out
of the model to avoid leakage.

**On the roadmap (from conservation-expert feedback).**
- Full-landscape prediction surface once the dense Earth Engine extraction runs.
- Richer prioritization inputs: dedicated fire-perimeter history (CAL FIRE / MTBS)
  and an authoritative land-ownership layer.
- Positioning against established tools such as the USGS Fire Danger Forecast
  (see docs/positioning.md).

**Use cases.**
- Prioritize monitoring
- Support restoration-planning discussions
- Identify areas for closer review
- Start expert-feedback conversations
            """
        )


def main() -> None:
    """Run the EcoRiskAI Streamlit dashboard."""
    st.set_page_config(page_title="EcoRiskAI", page_icon="🌲", layout="wide")
    inject_theme()

    st.markdown(
        '<div class="eco-header">'
        "<div>"
        '<div class="eco-title">🌲 EcoRiskAI</div>'
        '<div class="eco-sub">Conservation risk prioritization · Sierra Nevada, California</div>'
        "</div>"
        '<span class="eco-badge">⛰️ Sierra Nevada Conservation Risk</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    loaded = load_predictions()
    if loaded is None:
        st.error("Prediction file not found. Run `python main.py` first, then reload this dashboard.")
        return
    df, is_landscape = loaded

    if "prediction_source" in df.columns and (df["prediction_source"] == "heuristic_mvp_risk").any():
        st.warning(
            "Showing heuristic MVP risk because the XGBoost model was not available or could not train."
        )

    filtered = sidebar_filters(df)
    show_analytics(filtered)
    st.divider()

    if filtered.empty:
        show_map(filtered, None)
        return

    terciles = compute_terciles(filtered)

    top_col, perf_col = st.columns([1, 1], gap="large")
    with top_col:
        show_top_priorities(filtered)
    with perf_col:
        show_model_performance_card()
    with st.expander("What drives the risk score"):
        show_feature_importance()
    st.divider()

    # One selected area drives the map highlight, table, and details panel.
    # Year/month scoping comes only from the left filter panel.
    ranked = filtered.sort_values("predicted_risk_probability", ascending=False)
    area_options = list(dict.fromkeys(ranked["area_id"].tolist()))
    display_table = build_display_table(filtered, terciles)

    # Sync any map/table click into the selectbox before it is created.
    if st.session_state.get("area_select") not in area_options:
        st.session_state.pop("area_select", None)
    apply_pending_selections(display_table, area_options)

    selected_area = st.selectbox(
        "Selected area",
        area_options,
        key="area_select",
        help="Pick an area here, or click a marker on the map or a row in the table.",
    )

    area_records = ranked[ranked["area_id"] == selected_area].reset_index(drop=True)
    selected_row = area_records.iloc[0]
    if len(area_records) > 1:
        st.caption(
            f"This area has {len(area_records)} records in the current filters; "
            "showing the highest-risk one. Narrow the Year/Month filters to pick a specific period."
        )

    map_col, key_col = st.columns([2, 1], gap="large")
    with map_col:
        if is_landscape:
            st.caption(f"🗺️ Wall-to-wall risk surface · {len(filtered):,} grid cells")
        else:
            st.caption(
                f"🗺️ Sampled coverage · {len(filtered):,} grid cells. "
                "Run the Earth Engine extraction (earth_engine/) for a full-landscape surface."
            )
        show_map(filtered, selected_row)
    with key_col:
        show_map_key(filtered)
        show_signal_glossary()

    st.divider()
    section_header("🌲", "Risk table")
    st.caption("Every area for the current filters, ranked by risk score.")
    show_table(display_table)
    st.download_button(
        "⬇️ Download this view (CSV)",
        data=display_table.to_csv(index=False).encode("utf-8"),
        file_name="ecoriskai_risk_view.csv",
        mime="text/csv",
        help="Download the areas currently shown, with your filters applied.",
    )

    st.divider()
    section_header("📍", "Selected area details")
    detail_col, priority_col = st.columns([3, 2], gap="large")
    with detail_col:
        show_selected_details(selected_row, terciles)
        show_risk_trend(df, selected_row)
    with priority_col:
        show_prioritization(df, selected_row)

    st.divider()
    show_methodology()


if __name__ == "__main__":
    main()
