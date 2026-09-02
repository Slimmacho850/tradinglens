import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

# Ensure src directory is in sys.path for cloud deployment compatibility
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics_engine import (
    CONTRACT_SPECS,
    calculate_trade_plan,
    run_strategy_backtest,
    calc_cumulative_edge_curve,
    build_inter_session_matrix,
    build_hod_lod_heatmap_data,
)

# ============================================================
# DR LENS - STATISTICAL TRADING RESEARCH PLATFORM
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
DATABASE_DIR = ROOT / "database"
DISTRIBUTIONS_DIR = DATABASE_DIR / "distributions"
EVENTS_FILE = DATABASE_DIR / "events_2024.csv"

# Color Palette & Tokens
TEAL_PRIMARY = "#00E5A3"
TEAL_DARK = "#009E73"
TEAL_LIGHT = "#5CFFD0"
BG_DARK = "#0E1012"
BG_SIDEBAR = "#090A0C"
BG_CARD = "#14171A"
BORDER_COLOR = "#22272B"
TEXT_PRIMARY = "#F2F5F8"
TEXT_MUTED = "#8E97A0"
ACCENT_RED = "#FF4D4D"
ACCENT_BLUE = "#38BDF8"

st.set_page_config(
    page_title="DR Lens | Quantitative Trading Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS STYLING
# ============================================================

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    color: {TEXT_PRIMARY};
}}

.stApp {{
    background-color: {BG_DARK};
}}

[data-testid="stSidebar"] {{
    background-color: {BG_SIDEBAR};
    border-right: 1px solid {BORDER_COLOR};
}}

.block-container {{
    padding-top: 1.0rem;
    padding-bottom: 2rem;
    max-width: 1560px;
}}

/* Top Brand */
.brand-header {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 4px;
}}

.brand-badge {{
    background: linear-gradient(135deg, {TEAL_PRIMARY}, {TEAL_DARK});
    color: #000000;
    font-size: 18px;
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 6px;
    letter-spacing: 0.5px;
}}

.brand-title {{
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: {TEXT_PRIMARY};
}}

/* Section Titles */
.section-question {{
    font-size: 15px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    margin-top: 8px;
    margin-bottom: 8px;
}}

/* Metric Cards */
.metric-box {{
    background: linear-gradient(180deg, #181B1E 0%, #121417 100%);
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    padding: 12px 14px;
    min-height: 86px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.2s ease;
}}

.metric-box:hover {{
    border-color: #353B41;
    transform: translateY(-1px);
}}

.metric-lbl {{
    font-size: 11.5px;
    font-weight: 600;
    color: {TEXT_MUTED};
    letter-spacing: 0.2px;
    white-space: nowrap;
}}

.metric-val {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
    font-family: 'Inter', sans-serif;
    margin-top: 4px;
}}

/* Divider */
hr {{
    border: 0;
    border-top: 1px solid {BORDER_COLOR};
    margin: 16px 0;
}}

/* Streamlit Widget Overrides */
div[data-baseweb="select"] > div {{
    background-color: #171A1D !important;
    border-color: {BORDER_COLOR} !important;
    border-radius: 6px !important;
}}

div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
    background-color: {TEAL_PRIMARY} !important;
    color: #000000 !important;
    font-weight: 600 !important;
    border-radius: 4px !important;
}}

.stButton > button {{
    background-color: #1A1E22;
    color: {TEXT_MUTED};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 600;
    padding: 4px 10px;
    width: 100%;
    transition: all 0.15s ease;
}}

.stButton > button:hover {{
    background-color: #24292F;
    color: {TEAL_PRIMARY};
    border-color: {TEAL_PRIMARY};
}}

.stButton > button:focus, .stButton > button:active {{
    background-color: {TEAL_PRIMARY} !important;
    color: #000000 !important;
    border-color: {TEAL_PRIMARY} !important;
}}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================
# HELPER FORMATTING FUNCTIONS
# ============================================================

def to_bool(val: Any) -> bool | None:
    if isinstance(val, (pd.Series, np.ndarray, list)):
        return [to_bool(x) for x in val]
    if pd.isna(val):
        return None
    if isinstance(val, (bool, np.bool_)):
        return bool(val)
    s = str(val).strip().lower()
    return s in ["true", "1", "yes", "t"]


def make_15m_bucket(minute_val: int) -> str:
    start_min = int(minute_val)
    end_min = start_min + 15
    s_h, s_m = (start_min // 60) % 24, start_min % 60
    e_h, e_m = (end_min // 60) % 24, end_min % 60
    return f"{s_h:02d}:{s_m:02d}–{e_h:02d}:{e_m:02d}"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "trading_date" in out.columns:
        out["trading_date"] = pd.to_datetime(out["trading_date"], errors="coerce")
        out["day_of_week"] = out["trading_date"].dt.day_name()
    if "confirmation_time" in out.columns:
        out["confirmation_time"] = pd.to_datetime(out["confirmation_time"], errors="coerce")
        out["conf_30m_bucket"] = out["confirmation_time"].apply(make_30m_bucket)
    return out


def make_30m_bucket(dt: Any) -> str:
    if pd.isna(dt):
        return "Unknown"
    if isinstance(dt, str):
        try:
            dt = pd.to_datetime(dt)
        except Exception:
            return "Unknown"
    h = dt.hour
    m = dt.minute
    if m < 30:
        return f"{h:02d}:00-{h:02d}:30"
    else:
        next_h = (h + 1) % 24
        return f"{h:02d}:30-{next_h:02d}:00"


def pct_value(num: float | None) -> str:
    if num is None or math.isnan(num):
        return "—"
    return f"{num:.1f}%"


def sd_mult(num: float | None) -> str:
    if num is None or math.isnan(num):
        return "—"
    return f"{num:.1f}x"


def mean_clock(series: pd.Series) -> str:
    s = pd.to_datetime(series, errors="coerce").dropna()
    if s.empty:
        return "—"
    minutes = s.dt.hour * 60 + s.dt.minute
    mean_min = int(round(minutes.mean()))
    return f"{mean_min // 60:02d}:{mean_min % 60:02d}"


def median_clock(series: pd.Series) -> str:
    s = pd.to_datetime(series, errors="coerce").dropna()
    if s.empty:
        return "—"
    minutes = s.dt.hour * 60 + s.dt.minute
    med_min = int(round(minutes.median()))
    return f"{med_min // 60:02d}:{med_min % 60:02d}"


def render_metric_card(label: str, value: str, subtext: str = ""):
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-lbl">{label}</div>
            <div class="metric-val">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# DATA ENGINE
# ============================================================

def get_db_mtime() -> float:
    master_file = DATABASE_DIR / "events_master.csv"
    if master_file.exists():
        return master_file.stat().st_mtime
    elif EVENTS_FILE.exists():
        return EVENTS_FILE.stat().st_mtime
    return 0.0


@st.cache_data(show_spinner=False)
def load_dataset(mtime: float = 0.0) -> pd.DataFrame:
    master_file = DATABASE_DIR / "events_master.csv"
    if master_file.exists():
        df = pd.read_csv(master_file)
    elif EVENTS_FILE.exists():
        df = pd.read_csv(EVENTS_FILE)
    else:
        alt_files = sorted(DATABASE_DIR.glob("events_*.csv"))
        if alt_files:
            frames = [pd.read_csv(f) for f in alt_files]
            df = pd.concat(frames, ignore_index=True)
        else:
            return pd.DataFrame()

    df = df.drop_duplicates(subset=["instrument", "trading_date", "range_type"]).reset_index(drop=True)

    df["trading_date"] = pd.to_datetime(df["trading_date"], errors="coerce")
    df["day_of_week"] = df["trading_date"].dt.day_name()
    df["month"] = df["trading_date"].dt.month_name()
    df["week_of_month"] = df["trading_date"].dt.day.apply(lambda d: f"Week {(d-1)//7 + 1}")
    df["date_str"] = df["trading_date"].dt.strftime("%Y-%m-%d")

    df["confirmation_time"] = pd.to_datetime(df["confirmation_time"], errors="coerce")
    df["conf_30m_bucket"] = df["confirmation_time"].apply(make_30m_bucket)

    for col in ["extension_sd", "max_retracement_sd", "retracement_before_extreme_sd", "retracement_after_05_sd", "mean_sd_up", "mean_sd_down"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["confirmed", "dr_rule_true", "retraced_into_dr", "outside_dr_closed", "reached_05_sd"]:
        if col in df.columns:
            df[col] = df[col].apply(to_bool)

    return df


def filter_data(
    df: pd.DataFrame,
    instrument: str = "All",
    year_filter: str = "All",
    day_filter: str = "Unfiltered",
    range_type: str = "All",
    direction: str = "All",
    conf_time_buckets: list[str] | None = None,
    dr_rule_filter: str = "All",
) -> pd.DataFrame:
    out = df.copy()

    if instrument not in ["All", "All Instruments"] and "instrument" in out.columns:
        out = out[out["instrument"] == instrument]

    if year_filter not in ["All", "All Years"] and "trading_date" in out.columns:
        try:
            target_yr = int(year_filter)
            out = out[out["trading_date"].dt.year == target_yr]
        except ValueError:
            pass

    if day_filter != "Unfiltered":
        if day_filter in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            out = out[out["day_of_week"] == day_filter]
        elif day_filter.startswith("Week "):
            out = out[out["week_of_month"] == day_filter]
        elif day_filter in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]:
            out = out[out["month"] == day_filter]

    if range_type != "All" and "range_type" in out.columns:
        out = out[out["range_type"] == range_type]

    if direction != "All" and "direction" in out.columns:
        out = out[out["direction"] == direction]

    if dr_rule_filter != "All" and "dr_rule_true" in out.columns:
        target_rule = True if dr_rule_filter == "True" else False
        out = out[out["dr_rule_true"] == target_rule]

    if conf_time_buckets and len(conf_time_buckets) > 0 and "conf_30m_bucket" in out.columns:
        out = out[out["conf_30m_bucket"].isin(conf_time_buckets)]

    return out.reset_index(drop=True)


def calc_overview_kpis(base_df: pd.DataFrame, confirmed_df: pd.DataFrame) -> dict[str, str]:
    res = {}
    if len(base_df) > 0:
        conf_rate = (len(confirmed_df) / len(base_df)) * 100
        res["Conf. DR"] = pct_value(conf_rate)
    else:
        res["Conf. DR"] = "—"

    if "dr_rule_true" in confirmed_df.columns and len(confirmed_df) > 0:
        valid_dr_rule = confirmed_df["dr_rule_true"].dropna()
        res["DR true (%)"] = pct_value(valid_dr_rule.mean() * 100) if not valid_dr_rule.empty else "—"
    else:
        res["DR true (%)"] = "—"

    if "direction" in confirmed_df.columns and len(confirmed_df) > 0:
        long_pct = (confirmed_df["direction"] == "LONG").mean() * 100
        res["Conf. Long (%)"] = pct_value(long_pct)
    else:
        res["Conf. Long (%)"] = "—"

    if "retraced_into_dr" in confirmed_df.columns and len(confirmed_df) > 0:
        ret_pct = (confirmed_df["retraced_into_dr"] == True).mean() * 100
        res["Ret. into DR"] = pct_value(ret_pct)
    else:
        res["Ret. into DR"] = "—"

    if "outside_dr_closed" in confirmed_df.columns and len(confirmed_df) > 0:
        retraced_subset = confirmed_df[confirmed_df["retraced_into_dr"] == True]
        if not retraced_subset.empty:
            out_pct = (retraced_subset["outside_dr_closed"] == True).mean() * 100
            res["Outside DR (%)"] = pct_value(out_pct)
        else:
            res["Outside DR (%)"] = "—"
    else:
        res["Outside DR (%)"] = "—"

    if "mean_sd_up" in confirmed_df.columns and len(confirmed_df) > 0:
        up_vals = confirmed_df["mean_sd_up"].dropna()
        res["Mean SD Up"] = f"{up_vals.mean():.1f} x" if not up_vals.empty else "—"
    else:
        res["Mean SD Up"] = "—"

    if "mean_sd_down" in confirmed_df.columns and len(confirmed_df) > 0:
        down_vals = confirmed_df["mean_sd_down"].dropna()
        res["Mean SD Down"] = f"{down_vals.mean():.1f} x" if not down_vals.empty else "—"
    else:
        res["Mean SD Down"] = "—"

    if "confirmation_time" in confirmed_df.columns and len(confirmed_df) > 0:
        res["Avg. Conf. time"] = mean_clock(confirmed_df["confirmation_time"])
    else:
        res["Avg. Conf. time"] = "—"

    return res


def calc_core_metrics(df: pd.DataFrame) -> dict[str, str]:
    res = {}
    if "extension_sd" in df.columns:
        ext_s = df["extension_sd"].dropna()
        res["Median SD Extension"] = sd_mult(ext_s.median()) if not ext_s.empty else "—"
    else:
        res["Median SD Extension"] = "—"

    if "max_retracement_sd" in df.columns:
        ret_s = df["max_retracement_sd"].dropna()
        res["Median Max Retracement"] = sd_mult(ret_s.median()) if not ret_s.empty else "—"
    else:
        res["Median Max Retracement"] = "—"

    if "retracement_before_extreme_sd" in df.columns:
        ret_b_s = df["retracement_before_extreme_sd"].dropna()
        res["Median Retracement before HoD/LoD"] = sd_mult(ret_b_s.median()) if not ret_b_s.empty else "—"
    else:
        res["Median Retracement before HoD/LoD"] = "—"

    if "retracement_after_05_sd" in df.columns:
        ret_05_s = df["retracement_after_05_sd"].dropna()
        res["Median Retracement after 0.5 SD reached"] = sd_mult(ret_05_s.median()) if not ret_05_s.empty else "—"
    else:
        res["Median Retracement after 0.5 SD reached"] = "—"

    if "extension_time" in df.columns:
        res["Max Extension Median Time"] = median_clock(df["extension_time"])
    else:
        res["Max Extension Median Time"] = "—"

    return res


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    raw_df = load_dataset(get_db_mtime())

    if raw_df.empty:
        st.error("⚠️ No historical event data found. Please run the database builder.")
        return

    # Session State
    if "active_distribution" not in st.session_state:
        st.session_state["active_distribution"] = "extension_sd"
    if "active_view" not in st.session_state:
        st.session_state["active_view"] = "Dashboard"

    # Top Brand Header & View Switcher
    top_col1, top_col2 = st.columns([2.5, 3.5])
    with top_col1:
        st.markdown(
            """
            <div class="brand-header">
                <div class="brand-badge">77</div>
                <div class="brand-title">DR LENS</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_col2:
        nav_options = [
            "Dashboard",
            "Trade Calculator",
            "Strategy Backtester",
            "Edge Curves",
            "Confluence",
            "Timing Heatmap",
            "Distributions",
        ]
        active_view = st.radio(
            "View Navigation",
            nav_options,
            key="main_nav_radio",
            horizontal=True,
            label_visibility="collapsed",
            format_func=lambda x: f"▷ {x}",
        )

    # ========================================================
    # SIDEBAR
    # ========================================================
    with st.sidebar:
        st.markdown("### Global Settings")

        instrument_options = ["Gold (GC / XAU)", "Nasdaq (NQ)", "Emini S&P", "All Instruments"]
        instrument_choice = st.selectbox("Select Instrument", instrument_options, index=0)
        if "Gold" in instrument_choice or "GC" in instrument_choice:
            instrument = "GC"
        elif instrument_choice == "Emini S&P":
            instrument = "ES"
        elif instrument_choice == "Nasdaq (NQ)":
            instrument = "NQ"
        else:
            instrument = "All"

        years = sorted(raw_df["trading_date"].dropna().dt.year.unique().tolist(), reverse=True)
        min_year = min(years) if years else 2010
        max_year = max(years) if years else 2026
        year_options = [f"All Years ({min_year} - {max_year})"] + [str(y) for y in years]
        selected_year = st.selectbox("Select Year", year_options, index=0)
        year_filter = "All" if "All" in selected_year else selected_year

        range_type = st.radio("Select DR Range", ["ADR", "ODR", "RDR"], index=0)

        st.markdown("#### Session Filtering")
        filter_options = [
            "Entire Dataset", "Week 1", "Week 2", "Week 3", "Week 4",
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        selected_filter = st.selectbox("Select data", filter_options, index=0)
        sidebar_day_filter = "Unfiltered" if selected_filter == "Entire Dataset" else selected_filter

        st.divider()
        st.caption(f"Historical Sample: **{len(raw_df):,}** sessions")
        st.caption(f"Range: **{range_type}** | Instrument: **{instrument}**")

    # Global Base Population
    base_population = filter_data(
        raw_df,
        instrument=instrument,
        year_filter=year_filter,
        day_filter=sidebar_day_filter,
        range_type=range_type,
        direction="All",
        dr_rule_filter="All",
    )
    confirmed_population = base_population[base_population["confirmed"] == True].copy()

    # ========================================================
    # VIEW 1: DASHBOARD (Exact Replica of drlens.themas7er.com)
    # ========================================================
    if active_view == "Dashboard":

        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            st.markdown('<div class="section-question">How do you want to filter your data?</div>', unsafe_allow_html=True)
            filter_mode = st.selectbox(
                "How do you want to filter your data?",
                ["By day", "By week", "By month", "Entire Dataset"],
                index=0,
                label_visibility="collapsed",
            )

        with filter_col2:
            if filter_mode == "By day":
                st.markdown('<div class="section-question">Select day</div>', unsafe_allow_html=True)
                selected_day_abbr = st.selectbox(
                    "Select day",
                    ["Mon", "Tue", "Wed", "Thu", "Fri"],
                    index=0,
                    label_visibility="collapsed",
                )
                day_name_map = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday"}
                active_day_filter = day_name_map[selected_day_abbr]
            elif filter_mode == "By week":
                st.markdown('<div class="section-question">Select week</div>', unsafe_allow_html=True)
                active_day_filter = st.selectbox(
                    "Select week",
                    ["Week 1", "Week 2", "Week 3", "Week 4"],
                    index=0,
                    label_visibility="collapsed",
                )
            elif filter_mode == "By month":
                st.markdown('<div class="section-question">Select month</div>', unsafe_allow_html=True)
                active_day_filter = st.selectbox(
                    "Select month",
                    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
                    index=0,
                    label_visibility="collapsed",
                )
            else:
                st.markdown('<div class="section-question">&nbsp;</div>', unsafe_allow_html=True)
                active_day_filter = sidebar_day_filter

        active_base = filter_data(
            raw_df,
            instrument=instrument,
            year_filter=year_filter,
            day_filter=active_day_filter,
            range_type=range_type,
            direction="All",
            dr_rule_filter="All",
        )
        active_confirmed = active_base[active_base["confirmed"] == True].copy()

        overview_kpis = calc_overview_kpis(active_base, active_confirmed)

        kpi_cols = st.columns(8)
        kpi_labels = [
            "Conf. DR", "DR true (%)", "Conf. Long (%)", "Ret. into DR",
            "Outside DR (%)", "Mean SD Up", "Mean SD Down", "Avg. Conf. time",
        ]
        for col, label in zip(kpi_cols, kpi_labels):
            with col:
                render_metric_card(label, overview_kpis.get(label, "—"))

        st.markdown("<hr/>", unsafe_allow_html=True)

        st.markdown('<div class="section-question">Do you want to narrow down your data further?</div>', unsafe_allow_html=True)
        narrow_col1, narrow_col2, narrow_col3 = st.columns([1.5, 1.5, 5])

        with narrow_col1:
            st.markdown("**DR Rule**")
            dr_rule_selection = st.radio("DR Rule", ["True", "False", "All"], index=2, horizontal=True, label_visibility="collapsed")

        with narrow_col2:
            st.markdown("**Confirmation Direction**")
            direction_selection = st.radio("Confirmation Direction", ["Long", "Short", "All"], index=0, horizontal=True, label_visibility="collapsed")

        with narrow_col3:
            st.markdown("**Confirmation Time of the day**")
            available_buckets = sorted(
                active_confirmed["conf_30m_bucket"].dropna().unique().tolist(),
                key=lambda x: int(x[:2]) * 60 + int(x[3:5]) if "-" in x else 0,
            )
            if not available_buckets:
                available_buckets = ["20:30-21:00", "21:00-21:30", "21:30-22:00", "22:00-22:30", "22:30-23:00", "23:00-23:30"]

            default_bucket = ["20:30-21:00"] if ("20:30-21:00" in available_buckets and range_type == "ADR") else []
            selected_time_buckets = st.multiselect("Confirmation Time of the day", available_buckets, default=default_bucket, label_visibility="collapsed")

        direction_filter = direction_selection.upper() if direction_selection in ["Long", "Short"] else "All"
        filtered_events = filter_data(
            active_confirmed,
            instrument="All",
            day_filter="Unfiltered",
            range_type="All",
            direction=direction_filter,
            conf_time_buckets=selected_time_buckets if selected_time_buckets else None,
            dr_rule_filter=dr_rule_selection,
        )

        st.markdown("<hr/>", unsafe_allow_html=True)

        core_metrics = calc_core_metrics(filtered_events)
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

        with m_col1:
            render_metric_card("Median SD Extension", core_metrics.get("Median SD Extension", "—"))
            if st.button("See SD Extension distribution", key="btn_ext"):
                st.session_state["active_distribution"] = "extension_sd"

        with m_col2:
            render_metric_card("Median Max Retracement", core_metrics.get("Median Max Retracement", "—"))
            if st.button("See Max Retracement distribution", key="btn_ret"):
                st.session_state["active_distribution"] = "max_retracement_sd"

        with m_col3:
            render_metric_card("Median Retracement before HoD/LoD", core_metrics.get("Median Retracement before HoD/LoD", "—"))
            if st.button("See before HoD/LoD distribution", key="btn_hod"):
                st.session_state["active_distribution"] = "retracement_before_extreme_sd"

        with m_col4:
            render_metric_card("Median Retracement after 0.5 SD reached", core_metrics.get("Median Retracement after 0.5 SD reached", "—"))
            if st.button("See after 0.5 SD distribution", key="btn_05"):
                st.session_state["active_distribution"] = "retracement_after_05_sd"

        with m_col5:
            render_metric_card("Max Extension Median Time", core_metrics.get("Max Extension Median Time", "—"))
            st.markdown('<div style="height: 38px;"></div>', unsafe_allow_html=True)

        active_dist_field = st.session_state.get("active_distribution", "extension_sd")
        titles = {
            "extension_sd": "SD Max Extension - Distribution",
            "max_retracement_sd": "Maximum Retracement - Distribution",
            "retracement_before_extreme_sd": "Retracement Before HoD/LoD - Distribution",
            "retracement_after_05_sd": "Retracement After 0.5 SD Reached - Distribution",
        }
        dist_title = titles.get(active_dist_field, "Distribution")

        if not filtered_events.empty and active_dist_field in filtered_events.columns:
            plot_series = filtered_events[active_dist_field].dropna()
            if not plot_series.empty:
                if active_dist_field == "extension_sd":
                    edge_points = [round(i * 0.20, 2) for i in range(30)]
                    bins = [-np.inf] + edge_points[1:] + [np.inf]
                    labels = [f"{pt:.2f}" for pt in edge_points[:-1]] + ["5.80+"]
                elif active_dist_field == "max_retracement_sd":
                    edge_points = [round(i * 0.20, 2) for i in range(16)]
                    bins = [-np.inf] + edge_points[1:] + [np.inf]
                    labels = [f"{pt:.2f}" for pt in edge_points[:-1]] + ["3.00+"]
                else:
                    edge_points = [round(i * 0.20, 2) for i in range(11)]
                    bins = [-np.inf] + edge_points[1:] + [np.inf]
                    labels = [f"{pt:.2f}" for pt in edge_points[:-1]] + ["2.00+"]

                binned = pd.cut(plot_series, bins=bins, labels=labels, right=False)
                counts_df = binned.value_counts(sort=False).reset_index()
                counts_df.columns = ["bin", "count"]
                counts_df["percentage"] = (counts_df["count"] / len(plot_series) * 100).round(1)

                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        x=counts_df["bin"],
                        y=counts_df["count"],
                        marker=dict(color=TEAL_PRIMARY, line=dict(color=TEAL_PRIMARY, width=0.5)),
                        hovertemplate="<b>SD Level: %{x}</b><br>Count: %{y}<br>Share: %{customdata}%<extra></extra>",
                        customdata=counts_df["percentage"],
                    )
                )
                fig.update_layout(
                    title=dict(text=f"<b>{dist_title}</b> (N = {len(plot_series):,})", font=dict(color=TEXT_PRIMARY, size=14), x=0.5, xanchor="center", y=0.98),
                    template="plotly_dark",
                    paper_bgcolor=BG_DARK,
                    plot_bgcolor=BG_DARK,
                    height=380,
                    margin=dict(l=20, r=20, t=40, b=40),
                    bargap=0.15,
                    xaxis=dict(title=dict(text=dist_title, font=dict(color=TEXT_MUTED, size=11)), tickfont=dict(color=TEXT_MUTED, size=10), showgrid=False),
                    yaxis=dict(title=dict(text="Count", font=dict(color=TEXT_MUTED, size=11)), tickfont=dict(color=TEXT_PRIMARY, size=10), gridcolor="#1F2327", showgrid=True),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No numerical observations available for this metric under current filters.")
        else:
            st.info("No confirmed events matching current granular filters.")

    # ========================================================
    # VIEW 2: LIVE TRADE CALCULATOR & RISK PLANNER
    # ========================================================
    elif active_view == "Trade Calculator":
        st.markdown("### 🧮 Live Session Trade Calculator & Position Sizer")
        st.caption("Input today's active Defining Range to instantly generate exact limit entry prices, profit target tiers, position sizing, and historical hit probabilities.")

        calc_col1, calc_col2 = st.columns([1.8, 3.2])

        with calc_col1:
            live_instrument = st.selectbox("Trading Contract", ["Gold (GC - Standard)", "Gold (MGC - Micro)", "NQ (E-mini)", "MNQ (Micro)", "ES (E-mini)", "MES (Micro)"], index=0)
            if "MGC" in live_instrument:
                live_sym = "MGC"
            elif "GC" in live_instrument or "Gold" in live_instrument:
                live_sym = "GC"
            elif "MNQ" in live_instrument:
                live_sym = "MNQ"
            elif "NQ" in live_instrument:
                live_sym = "NQ"
            elif "MES" in live_instrument:
                live_sym = "MES"
            else:
                live_sym = "ES"

            direction_input = st.radio("Confirmation Direction", ["LONG ↗", "SHORT ↘"], index=0, horizontal=True)
            active_dir = "LONG" if "LONG" in direction_input else "SHORT"

            if "GC" in live_sym or "MGC" in live_sym:
                default_high = 2750.0
                default_low = 2735.0
            elif "NQ" in live_sym or "MNQ" in live_sym:
                default_high = 20150.0
                default_low = 20080.0
            else:
                default_high = 5520.0
                default_low = 5500.0

            inp_col1, inp_col2 = st.columns(2)
            with inp_col1:
                input_dr_high = st.number_input("DR High", value=default_high, step=1.0, format="%.2f")
            with inp_col2:
                input_dr_low = st.number_input("DR Low", value=default_low, step=1.0, format="%.2f")

            st.markdown("#### 2. Execution Strategy")
            entry_model = st.selectbox(
                "Limit Entry Level",
                ["Mid-DR (0.50x Retracement)", "DR Boundary (0.00x Retracement)", "25% Retracement (0.25x)", "75% Retracement (0.75x)"],
                index=0,
            )
            entry_sd_map = {"Mid-DR (0.50x Retracement)": 0.5, "DR Boundary (0.00x Retracement)": 0.0, "25% Retracement (0.25x)": 0.25, "75% Retracement (0.75x)": 0.75}
            active_entry_sd = entry_sd_map[entry_model]

            st.markdown("#### 3. Account & Risk Management")
            acc_col1, acc_col2 = st.columns(2)
            with acc_col1:
                account_val = st.number_input("Account Equity ($)", value=25000.0, step=1000.0)
            with acc_col2:
                risk_pct_val = st.number_input("Risk Per Trade (%)", value=1.0, step=0.25, max_value=5.0)

        # Compute Plan
        plan = calculate_trade_plan(
            dr_high=input_dr_high,
            dr_low=input_dr_low,
            direction=active_dir,
            entry_retrace_sd=active_entry_sd,
            stop_loss_sd=1.0,
            instrument=live_sym,
            account_size=account_val,
            risk_pct=risk_pct_val,
        )

        with calc_col2:
            st.markdown("#### 📊 Execution Order Blueprint")

            p_col1, p_col2, p_col3, p_col4 = st.columns(4)
            with p_col1:
                render_metric_card("Entry Order", f"{plan.entry_price:.2f}")
            with p_col2:
                render_metric_card("Invalidation Stop", f"{plan.stop_price:.2f}")
            with p_col3:
                render_metric_card("Stop Distance", f"{plan.stop_distance_pts:.2f} pts")
            with p_col4:
                render_metric_card("Position Size", f"{plan.contracts} Contract(s)")

            st.markdown("#### Take-Profit Tiers & Mathematical Expectations")

            tp_rows = []
            for t in plan.targets:
                tp_rows.append({
                    "Target Tier": t["sd_level"],
                    "Exit Price": f"{t['tp_price']:.2f}",
                    "Gain (Pts)": f"+{t['gain_pts']:.2f} pts",
                    "Dollar Gain ($)": f"+${t['gain_dollars']:,.2f}",
                    "Risk:Reward": f"1 : {t['rr_ratio']:.2f}",
                })

            st.dataframe(pd.DataFrame(tp_rows), use_container_width=True, hide_index=True)

            # Price Map Chart
            st.markdown("#### 🗺️ Visual Price Level Structure")
            fig_map = go.Figure()

            # Target lines
            for t in plan.targets:
                fig_map.add_trace(go.Scatter(
                    x=[0, 1], y=[t["tp_price"], t["tp_price"]],
                    mode="lines+text", name=t["sd_level"],
                    text=["", f"TP {t['sd_level']} ({t['tp_price']:.2f}) - 1:{t['rr_ratio']:.1f} R:R"],
                    textposition="middle right",
                    line=dict(color=TEAL_LIGHT if t["sd_val"] <= 1.0 else "#00C896", width=1, dash="dot"),
                ))

            # Entry line
            fig_map.add_trace(go.Scatter(
                x=[0, 1], y=[plan.entry_price, plan.entry_price],
                mode="lines+text", name="Entry",
                text=["", f"★ ENTRY ({plan.entry_price:.2f})"],
                textposition="middle right",
                line=dict(color=TEAL_PRIMARY, width=3),
            ))

            # Stop line
            fig_map.add_trace(go.Scatter(
                x=[0, 1], y=[plan.stop_price, plan.stop_price],
                mode="lines+text", name="Stop Loss",
                text=["", f"🛑 STOP / INVALIDATION ({plan.stop_price:.2f})"],
                textposition="middle right",
                line=dict(color=ACCENT_RED, width=2, dash="dash"),
            ))

            fig_map.update_layout(
                template="plotly_dark",
                paper_bgcolor=BG_DARK,
                plot_bgcolor=BG_DARK,
                height=300,
                showlegend=False,
                margin=dict(l=10, r=180, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False, range=[0, 1.3]),
                yaxis=dict(gridcolor="#1F2327", showgrid=True),
            )
            st.plotly_chart(fig_map, use_container_width=True)

    # ========================================================
    # VIEW 3: SYSTEMATIC STRATEGY BACKTESTER
    # ========================================================
    elif active_view == "Strategy Backtester":
        min_year = int(raw_df["trading_date"].dropna().dt.year.min()) if not raw_df.empty else 2010
        max_year = int(raw_df["trading_date"].dropna().dt.year.max()) if not raw_df.empty else 2026
        span_years = max_year - min_year + 1
        st.markdown(f"### 🧪 {span_years}-Year Systematic Strategy Backtester & Simulator")
        st.caption(f"Simulate rule-based execution across {len(raw_df):,} historical sessions ({min_year}–{max_year}). Test entry retracements, stop loss variations, and take-profit targets.")

        bt_settings_col1, bt_settings_col2, bt_settings_col3, bt_settings_col4 = st.columns(4)

        with bt_settings_col1:
            bt_entry_choice = st.selectbox(
                "Entry Retracement Level",
                ["Mid-DR (0.50x SD)", "DR Level (0.00x SD)", "25% Retracement (0.25x SD)", "75% Retracement (0.75x SD)"],
                index=0,
            )
            bt_entry_sd = {"Mid-DR (0.50x SD)": 0.5, "DR Level (0.00x SD)": 0.0, "25% Retracement (0.25x SD)": 0.25, "75% Retracement (0.75x SD)": 0.75}[bt_entry_choice]

        with bt_settings_col2:
            bt_stop_choice = st.selectbox("Stop Loss Rule", ["Opposite DR (1.0x SD)", "Mid-DR (0.5x SD)"], index=0)
            bt_stop_sd = 1.0 if "1.0x" in bt_stop_choice else 0.5

        with bt_settings_col3:
            bt_tp_choice = st.selectbox("Take Profit Target", ["0.5x SD", "0.8x SD", "1.0x SD", "1.2x SD", "1.5x SD", "2.0x SD"], index=1)
            bt_tp_sd = float(bt_tp_choice.replace("x SD", ""))

        with bt_settings_col4:
            bt_early_filter = st.checkbox("Early Confirmation Only (<30m)", value=False)

        # Run Backtest
        bt_res = run_strategy_backtest(
            raw_df,
            entry_retrace_sd=bt_entry_sd,
            stop_loss_sd=bt_stop_sd,
            take_profit_sd=bt_tp_sd,
            account_size=25000.0,
            risk_pct_per_trade=1.0,
            early_time_filter_only=bt_early_filter,
            instrument=instrument,
            range_type=range_type,
        )

        st.markdown("#### Performance Scorecard")
        res_cols = st.columns(6)
        with res_cols[0]:
            render_metric_card("Total Trades", f"{bt_res.filled_trades:,}")
        with res_cols[1]:
            render_metric_card("Win Rate", f"{bt_res.win_rate_pct:.1f}%")
        with res_cols[2]:
            render_metric_card("Profit Factor", f"{bt_res.profit_factor:.2f}")
        with res_cols[3]:
            render_metric_card("Total Net PnL", f"${bt_res.total_pnl_dollars:,.2f}")
        with res_cols[4]:
            render_metric_card("Max Drawdown", f"{bt_res.max_drawdown_pct:.1f}%")
        with res_cols[5]:
            render_metric_card("Sharpe Ratio", f"{bt_res.sharpe_ratio:.2f}")

        st.markdown("#### 📈 15-Year Cumulative Equity Curve")
        if not bt_res.equity_curve.empty:
            fig_equity = px.line(
                bt_res.equity_curve,
                x="trading_date",
                y="equity",
                title="Portfolio Equity ($) Over 15 Years (Starting Balance: $25,000, Risk: 1% / trade)",
            )
            fig_equity.update_traces(line_color=TEAL_PRIMARY, line_width=1.5)
            fig_equity.update_layout(
                template="plotly_dark",
                paper_bgcolor=BG_DARK,
                plot_bgcolor=BG_DARK,
                height=380,
                xaxis=dict(title="Date", gridcolor="#1F2327"),
                yaxis=dict(title="Account Balance ($)", gridcolor="#1F2327"),
            )
            st.plotly_chart(fig_equity, use_container_width=True)

        if not bt_res.monthly_pnl_matrix.empty:
            st.markdown("#### 📅 Yearly & Monthly PnL Breakdown ($)")
            st.dataframe(bt_res.monthly_pnl_matrix.style.format("${:,.0f}"), use_container_width=True)

    # ========================================================
    # VIEW 4: CUMULATIVE EDGE & TAKE-PROFIT OPTIMIZER
    # ========================================================
    elif active_view == "Edge Curves":
        st.markdown("### 📈 Cumulative Probability Decay & Expected Value (EV) Optimizer")
        st.caption("Discover the exact mathematical sweet spot for your Take-Profit target to maximize long-term dollar growth.")

        opt_col1, opt_col2 = st.columns(2)
        with opt_col1:
            edge_entry_choice = st.selectbox("Entry Retracement Model", ["Mid-DR (0.50x Retracement)", "DR Level (0.00x)", "25% Retracement (0.25x)"], index=0)
            edge_entry_sd = 0.5 if "0.50x" in edge_entry_choice else (0.0 if "0.00x" in edge_entry_choice else 0.25)

        with opt_col2:
            edge_stop_choice = st.selectbox("Invalidation Stop Model", ["Opposite DR (1.00x SD)", "Mid-DR (0.50x SD)"], index=0)
            edge_stop_sd = 1.0 if "1.00x" in edge_stop_choice else 0.5

        edge_df = calc_cumulative_edge_curve(confirmed_population, entry_retrace_sd=edge_entry_sd, stop_loss_sd=edge_stop_sd)

        if not edge_df.empty:
            best_row = edge_df.loc[edge_df["expected_value_r"].idxmax()]

            st.markdown("#### 🏆 Optimal Take-Profit Discovery")
            opt_kpi1, opt_kpi2, opt_kpi3, opt_kpi4 = st.columns(4)
            with opt_kpi1:
                render_metric_card("Optimal Target", f"{best_row['sd_level']:.1f}x SD")
            with opt_kpi2:
                render_metric_card("Hit Probability", f"{best_row['probability_pct']:.1f}%")
            with opt_kpi3:
                render_metric_card("Risk : Reward", f"1 : {best_row['rr_ratio']:.1f}")
            with opt_kpi4:
                render_metric_card("Peak Expected Value", f"+{best_row['expected_value_r']:.2f} R / trade")

            fig_ev = go.Figure()
            fig_ev.add_trace(go.Scatter(
                x=edge_df["sd_level"], y=edge_df["probability_pct"],
                name="Reach Probability (%)", line=dict(color=ACCENT_BLUE, width=2),
                yaxis="y1",
            ))
            fig_ev.add_trace(go.Scatter(
                x=edge_df["sd_level"], y=edge_df["expected_value_r"],
                name="Expected Value (R)", line=dict(color=TEAL_PRIMARY, width=3),
                yaxis="y2",
            ))

            fig_ev.update_layout(
                title="<b>Empirical Reach Probability vs. Expected Value Curve (EV)</b>",
                template="plotly_dark",
                paper_bgcolor=BG_DARK,
                plot_bgcolor=BG_DARK,
                height=400,
                xaxis=dict(title="Target SD Level", gridcolor="#1F2327"),
                yaxis=dict(title="Probability (%)", side="left", gridcolor="#1F2327", range=[0, 100]),
                yaxis2=dict(title="Expected Value (R / trade)", side="right", overlaying="y", showgrid=False),
                legend=dict(x=0.8, y=0.95),
            )
            st.plotly_chart(fig_ev, use_container_width=True)

            st.dataframe(edge_df, use_container_width=True, hide_index=True)

    # ========================================================
    # VIEW 5: INTER-SESSION CONFLUENCE MATRIX
    # ========================================================
    elif active_view == "Confluence":
        st.markdown("### 🔄 Inter-Session Directional Flow & Confluence Matrix")
        st.caption("Analyze how momentum carries across consecutive trading sessions: **Asian (ADR) → London (ODR) → New York (RDR)**.")

        seq_df = build_inter_session_matrix(raw_df)
        if not seq_df.empty:
            st.dataframe(seq_df, use_container_width=True, hide_index=True)

            fig_seq = px.bar(
                seq_df,
                x="Sequence",
                y="Days",
                color="Category",
                title="Frequency of Daily Session Direction Permutations",
                template="plotly_dark",
            )
            fig_seq.update_layout(paper_bgcolor=BG_DARK, plot_bgcolor=BG_DARK, height=380)
            st.plotly_chart(fig_seq, use_container_width=True)
        else:
            st.info("Insufficient multi-session records to compute confluence matrix.")

    # ========================================================
    # VIEW 6: TIMING & HOD/LOD HEATMAP
    # ========================================================
    elif active_view == "Timing Heatmap":
        st.markdown("### ⏰ Intraday High / Low of Day Timing Heatmap")
        st.caption(f"Identify peak volume and extreme price reversal windows across the trading week for {range_type} sessions.")

        heat_df = build_hod_lod_heatmap_data(raw_df, range_type=range_type)
        if not heat_df.empty:
            fig_heat = px.imshow(
                heat_df,
                labels=dict(x="30-Minute Time Window (ET)", y="Day of Week", color="Event Count"),
                color_continuous_scale="Viridis",
                title=f"Confirmation Time Distribution Matrix ({range_type})",
            )
            fig_heat.update_layout(template="plotly_dark", paper_bgcolor=BG_DARK, plot_bgcolor=BG_DARK, height=360)
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("No timing records available for selected range.")

    # ========================================================
    # VIEW 7: DISTRIBUTIONS & DATA EXPLORER
    # ========================================================
    elif active_view == "Distributions":
        st.markdown("### 📊 Comprehensive Statistical Distributions")
        st.caption(f"In-depth percentile matrices, range breakdowns, and raw event data for {range_type} sessions.")

        tab1, tab2, tab3 = st.tabs(["Percentile Tables", "Breakdown by Direction / Range", "Filtered Data Explorer"])

        with tab1:
            st.markdown("#### Key Metric Percentiles (SD Units)")
            metrics_to_show = ["extension_sd", "max_retracement_sd", "retracement_before_extreme_sd", "retracement_after_05_sd"]
            names_map = {
                "extension_sd": "Maximum SD Extension",
                "max_retracement_sd": "Maximum Retracement (SD)",
                "retracement_before_extreme_sd": "Retracement Before HoD/LoD (SD)",
                "retracement_after_05_sd": "Retracement After 0.5 SD (SD)",
            }

            rows = []
            for m in metrics_to_show:
                s = confirmed_population[m].dropna()
                if not s.empty:
                    rows.append({
                        "Metric": names_map[m],
                        "Mean": f"{s.mean():.2f}x",
                        "P10": f"{s.quantile(0.10):.2f}x",
                        "P25": f"{s.quantile(0.25):.2f}x",
                        "Median (P50)": f"{s.median():.2f}x",
                        "P75": f"{s.quantile(0.75):.2f}x",
                        "P90": f"{s.quantile(0.90):.2f}x",
                    })

            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("#### Range & Direction Comparison")
            comp_df = raw_df[raw_df["confirmed"] == True].groupby(["range_type", "direction"]).agg(
                Events=("confirmed", "count"),
                DR_Rule_True=("dr_rule_true", lambda x: f"{(x==True).mean()*100:.1f}%"),
                Retraced_into_DR=("retraced_into_dr", lambda x: f"{(x==True).mean()*100:.1f}%"),
                Outside_DR_Close=("outside_dr_closed", lambda x: f"{(x==True).mean()*100:.1f}%"),
                Median_Extension=("extension_sd", lambda x: f"{x.median():.2f}x"),
                Median_Max_Retracement=("max_retracement_sd", lambda x: f"{x.median():.2f}x"),
            ).reset_index()
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

        with tab3:
            st.markdown("#### Filtered Events Dataset")
            display_cols = [
                "trading_date", "day_of_week", "range_type", "direction",
                "confirmation_time", "confirmation_price", "dr_rule_true",
                "retraced_into_dr", "outside_dr_closed", "extension_sd",
                "max_retracement_sd", "retracement_before_extreme_sd"
            ]
            valid_cols = [c for c in display_cols if c in confirmed_population.columns]
            st.dataframe(confirmed_population[valid_cols], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
