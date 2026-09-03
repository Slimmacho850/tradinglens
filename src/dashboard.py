import datetime
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    build_hos_los_heatmap_data,
    build_retracement_time_matrix,
    build_time_bucket_distribution,
)
try:
    from weekly_updater import run_weekly_update
except ImportError:
    run_weekly_update = None

# ============================================================
# DR LENS - STATISTICAL TRADING RESEARCH PLATFORM
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
DATABASE_DIR = ROOT / "database"
DISTRIBUTIONS_DIR = DATABASE_DIR / "distributions"
EVENTS_FILE = DATABASE_DIR / "events_master.csv"
if not EVENTS_FILE.exists():
    EVENTS_FILE = DATABASE_DIR / "events_2024.csv"

# Color Palette & Tokens
TEAL_PRIMARY = "#00E5A3"
TEAL_DARK = "#009E73"
TEAL_LIGHT = "#5CFFD0"
BG_DARK = "#0A0D10"
BG_SIDEBAR = "#06080A"
BG_CARD = "#121519"
BORDER_COLOR = "#1F242A"
BORDER_HOVER = "#323B45"
TEXT_PRIMARY = "#F2F5F8"
TEXT_MUTED = "#8E97A0"
ACCENT_RED = "#FF4560"
ACCENT_BLUE = "#38BDF8"
ACCENT_GOLD = "#F59E0B"

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
    padding-top: 0.8rem;
    padding-bottom: 2rem;
    max-width: 1580px;
}}

/* Brand Header */
.brand-header {{
    display: flex;
    align-items: center;
    gap: 12px;
}}

.brand-badge {{
    background: linear-gradient(135deg, {TEAL_PRIMARY}, {TEAL_DARK});
    color: #000000;
    font-size: 17px;
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 6px;
    letter-spacing: 0.5px;
}}

.brand-title {{
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: {TEXT_PRIMARY};
}}

/* Live Status Notification Banner */
.status-banner {{
    background: linear-gradient(90deg, rgba(0, 229, 163, 0.08) 0%, rgba(18, 21, 25, 0.8) 100%);
    border: 1px solid rgba(0, 229, 163, 0.25);
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
}}

.status-banner.weekend {{
    background: linear-gradient(90deg, rgba(245, 158, 11, 0.08) 0%, rgba(18, 21, 25, 0.8) 100%);
    border-color: rgba(245, 158, 11, 0.3);
}}

/* Section Headings */
.section-question {{
    font-size: 14.5px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    margin-top: 6px;
    margin-bottom: 6px;
}}

/* Metric Cards */
.metric-box {{
    background: linear-gradient(180deg, #15181D 0%, #101317 100%);
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    padding: 12px 14px;
    min-height: 84px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.2s ease;
}}

.metric-box:hover {{
    border-color: {BORDER_HOVER};
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
    font-size: 21px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
    font-family: 'Inter', sans-serif;
    margin-top: 3px;
}}

/* Playbook Info Box */
.hud-box {{
    background: #111418;
    border: 1px solid {BORDER_COLOR};
    border-left: 3px solid {TEAL_PRIMARY};
    border-radius: 6px;
    padding: 12px 16px;
    margin: 10px 0;
}}

.hud-title {{
    font-size: 13px;
    font-weight: 700;
    color: {TEAL_PRIMARY};
    margin-bottom: 4px;
}}

.hud-desc {{
    font-size: 12px;
    color: {TEXT_MUTED};
    line-height: 1.4;
}}

/* Streamlit Input Overrides */
div[data-baseweb="select"] > div {{
    background-color: #14171C !important;
    border-color: {BORDER_COLOR} !important;
    border-radius: 6px !important;
    color: {TEXT_PRIMARY} !important;
}}

div[data-baseweb="input"] > div {{
    background-color: #14171C !important;
    border-color: {BORDER_COLOR} !important;
    color: {TEXT_PRIMARY} !important;
}}

input {{
    color: {TEXT_PRIMARY} !important;
    -webkit-text-fill-color: {TEXT_PRIMARY} !important;
}}

div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
    background-color: {TEAL_PRIMARY} !important;
    color: #000000 !important;
    font-weight: 600 !important;
    border-radius: 4px !important;
}}

.stButton > button {{
    background-color: #161A1F;
    color: {TEXT_MUTED};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 600;
    padding: 5px 10px;
    width: 100%;
    transition: all 0.15s ease;
}}

.stButton > button:hover {{
    background-color: #20262E;
    color: {TEAL_PRIMARY};
    border-color: {TEAL_PRIMARY};
}}

.stButton > button:focus, .stButton > button:active {{
    background-color: {TEAL_PRIMARY} !important;
    color: #000000 !important;
    border-color: {TEAL_PRIMARY} !important;
}}

hr {{
    border: 0;
    border-top: 1px solid {BORDER_COLOR};
    margin: 14px 0;
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

    # Vectorized unclipped retracement calculation (preserves negative retracement values when price never re-enters IDR/DR)
    if "max_retracement_price" in df.columns and "dr_high" in df.columns and "dr_range" in df.columns:
        long_mask = (df["confirmed"] == True) & (df["direction"] == "LONG") & (df["dr_range"] > 0)
        short_mask = (df["confirmed"] == True) & (df["direction"] == "SHORT") & (df["dr_range"] > 0)
        df.loc[long_mask, "max_retracement_sd"] = (df.loc[long_mask, "dr_high"] - df.loc[long_mask, "max_retracement_price"]) / df.loc[long_mask, "dr_range"]
        df.loc[short_mask, "max_retracement_sd"] = (df.loc[short_mask, "max_retracement_price"] - df.loc[short_mask, "dr_low"]) / df.loc[short_mask, "dr_range"]

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
    after_date: Optional[datetime.date] = None,
    last_x_days: Optional[int] = None,
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

    if after_date is not None and "trading_date" in out.columns:
        out = out[out["trading_date"].dt.date >= after_date]

    if last_x_days is not None and last_x_days > 0 and "trading_date" in out.columns:
        unique_dates = sorted(out["trading_date"].dropna().dt.date.unique())
        if len(unique_dates) > last_x_days:
            cutoff = unique_dates[-last_x_days]
            out = out[out["trading_date"].dt.date >= cutoff]

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
        res["Median Retracement before HoS/LoS"] = sd_mult(ret_b_s.median()) if not ret_b_s.empty else "—"
    else:
        res["Median Retracement before HoS/LoS"] = "—"

    if "retracement_after_05_sd" in df.columns:
        ret_05_s = df["retracement_after_05_sd"].dropna()
        res["Median Retracement after 0.5 SD reached"] = sd_mult(ret_05_s.median()) if not ret_05_s.empty else "—"
    else:
        res["Median Retracement after 0.5 SD reached"] = "—"

    if "first_retracement_time" in df.columns:
        res["First Retracement Median Time"] = median_clock(df["first_retracement_time"])
    else:
        res["First Retracement Median Time"] = "—"

    if "max_retracement_time" in df.columns:
        res["Max Retracement Median Time"] = median_clock(df["max_retracement_time"])
    else:
        res["Max Retracement Median Time"] = "—"

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

    now_dt = datetime.datetime.now()
    today_weekday_name = now_dt.strftime("%A")
    today_formatted = now_dt.strftime("%B %d, %Y")
    is_weekend = now_dt.weekday() >= 5  # 5 = Sat, 6 = Sun

    # Session State
    if "active_distribution" not in st.session_state:
        st.session_state["active_distribution"] = "extension_sd"
    if "active_view" not in st.session_state:
        st.session_state["active_view"] = "Dashboard"

    # Top Brand Header & View Switcher
    top_col1, top_col2 = st.columns([2.5, 4.0])
    with top_col1:
        st.markdown(
            """
            <div class="brand-header">
                <div class="brand-badge">⚡ DR</div>
                <div class="brand-title">DR LENS & DRIVE</div>
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
        st.markdown("### 🎛️ Global Controls")

        instrument_options = [
            "Emini S&P (ES)",
            "Nasdaq (NQ)",
            "Gold (GC / XAU)",
            "Emini Dow (YM)",
            "Euro FX (EURUSD / 6E)",
            "All Instruments",
        ]
        instrument_choice = st.selectbox("Select Instrument", instrument_options, index=0)
        if "Gold" in instrument_choice or "GC" in instrument_choice:
            instrument = "GC"
        elif "Emini S&P" in instrument_choice or "ES" in instrument_choice:
            instrument = "ES"
        elif "Nasdaq" in instrument_choice or "NQ" in instrument_choice:
            instrument = "NQ"
        elif "Dow" in instrument_choice or "YM" in instrument_choice:
            instrument = "YM"
        elif "Euro" in instrument_choice or "EURUSD" in instrument_choice or "6E" in instrument_choice:
            instrument = "6E"
        else:
            instrument = "All"

        years = sorted(raw_df["trading_date"].dropna().dt.year.unique().tolist(), reverse=True)
        min_year = min(years) if years else 2010
        max_year = max(years) if years else 2026
        year_options = [f"All Years ({min_year} - {max_year})"] + [str(y) for y in years]
        selected_year = st.selectbox("Select Year", year_options, index=0)
        year_filter = "All" if "All" in selected_year else selected_year

        range_type = st.radio("Select DR Range", ["ADR", "ODR", "RDR"], index=0, horizontal=True)

        st.markdown("#### 📅 Session Filtering")
        filter_mode_sidebar = st.selectbox(
            "Filter Scope",
            ["Entire Dataset (20 Years)", "After Chosen Date", "Last X Trading Days"],
            index=0,
        )

        after_date_val = None
        last_x_val = None

        if filter_mode_sidebar == "After Chosen Date":
            min_date = raw_df["trading_date"].min().date() if not raw_df.empty else datetime.date(2010, 1, 1)
            max_date = raw_df["trading_date"].max().date() if not raw_df.empty else datetime.date(2026, 12, 31)
            default_start = datetime.date(2023, 1, 1)
            after_date_val = st.date_input("Include data after", value=default_start, min_value=min_date, max_value=max_date)
        elif filter_mode_sidebar == "Last X Trading Days":
            last_x_val = st.slider("Number of recent sessions", min_value=50, max_value=2000, value=250, step=50)

        st.divider()
        st.markdown("#### 🔄 Weekly Maintenance")
        st.caption("Auto-ingests past week's 1m data for ES, NQ, GC, YM, 6E and updates the master database.")
        if st.button("⚡ Sync Past Week Data", key="btn_sync_week_sidebar"):
            with st.spinner("Fetching latest market data & recomputing Defining Ranges..."):
                sync_res = run_weekly_update(days_back=7)
                if sync_res.get("status") == "success":
                    st.success(f"✓ Synced! Database now has {sync_res['total_sessions']:,} sessions (Up to {sync_res['max_date']}).")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Sync finished with no new data.")

        st.divider()
        st.markdown("#### 📖 Field Manual & PDF Guide")
        pdf_file = ROOT / "DR_Lens_Comprehensive_Trading_Guide.pdf"
        if not pdf_file.exists():
            pdf_file = ROOT / "trading lens" / "DR_Lens_Comprehensive_Trading_Guide.pdf"
        if pdf_file.exists():
            with open(pdf_file, "rb") as f:
                st.download_button(
                    label="📥 Download PDF Trading Guide",
                    data=f.read(),
                    file_name="DR_Lens_Comprehensive_Trading_Guide.pdf",
                    mime="application/pdf",
                )

        st.caption(f"Historical Sample: **{len(raw_df):,}** sessions")
        st.caption(f"Active Range: **{range_type}** | Contract: **{instrument}**")

    # Global Base Population
    base_population = filter_data(
        raw_df,
        instrument=instrument,
        year_filter=year_filter,
        day_filter="Unfiltered",
        range_type=range_type,
        direction="All",
        dr_rule_filter="All",
        after_date=after_date_val,
        last_x_days=last_x_val,
    )
    confirmed_population = base_population[base_population["confirmed"] == True].copy()

    # ========================================================
    # VIEW 1: DASHBOARD (Master & Mage DR Lens Architecture)
    # ========================================================
    if active_view == "Dashboard":

        # Live Status & Weekend Notice Banner
        if is_weekend:
            st.markdown(
                f"""
                <div class="status-banner weekend">
                    <div><b>⚡ Weekend Notice:</b> Markets closed today ({today_weekday_name}, {today_formatted}). Showing default Monday historical edge baseline.</div>
                    <div style="font-weight:700; color:{ACCENT_GOLD};">GET READY FOR MONDAY</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="status-banner">
                    <div><b>🟢 Active Trading Session:</b> Today is <b>{today_weekday_name}, {today_formatted}</b>. 20-year statistical baseline loaded for <b>{range_type}</b>.</div>
                    <div style="font-weight:700; color:{TEAL_PRIMARY};">QUANT EDGE READY</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            st.markdown('<div class="section-question">How do you want to filter your data?</div>', unsafe_allow_html=True)
            filter_mode = st.selectbox(
                "How do you want to filter your data?",
                ["By day", "By week", "By month", "Entire Dataset (20 Years)"],
                index=0 if not is_weekend else 0,
                label_visibility="collapsed",
            )

        with filter_col2:
            if filter_mode == "By day":
                st.markdown('<div class="section-question">Select day</div>', unsafe_allow_html=True)
                selected_day_abbr = st.selectbox(
                    "Select day",
                    ["Mon", "Tue", "Wed", "Thu", "Fri"],
                    index=0 if is_weekend else (["Mon", "Tue", "Wed", "Thu", "Fri"].index(today_weekday_name[:3]) if today_weekday_name[:3] in ["Mon", "Tue", "Wed", "Thu", "Fri"] else 0),
                    label_visibility="collapsed",
                )
                day_name_map = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday"}
                active_day_filter = day_name_map[selected_day_abbr]
            elif filter_mode == "By week":
                st.markdown('<div class="section-question">Select week of month</div>', unsafe_allow_html=True)
                active_day_filter = st.selectbox(
                    "Select week",
                    ["Week 1", "Week 2", "Week 3", "Week 4"],
                    index=1,  # Default to Week 2 as in Master stream
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
                active_day_filter = "Unfiltered"

        active_base = filter_data(
            raw_df,
            instrument=instrument,
            year_filter=year_filter,
            day_filter=active_day_filter,
            range_type=range_type,
            direction="All",
            dr_rule_filter="All",
            after_date=after_date_val,
            last_x_days=last_x_val,
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
            st.markdown("**Confirmation Time of the day (30m Windows)**")
            available_buckets = sorted(
                active_confirmed["conf_30m_bucket"].dropna().unique().tolist(),
                key=lambda x: int(x[:2]) * 60 + int(x[3:5]) if "-" in x else 0,
            )
            if not available_buckets:
                if range_type == "ADR":
                    available_buckets = ["20:30-21:00", "21:00-21:30", "21:30-22:00", "22:00-22:30", "22:30-23:00", "23:00-23:30"]
                elif range_type == "ODR":
                    available_buckets = ["04:00-04:30", "04:30-05:00", "05:00-05:30", "05:30-06:00", "06:00-06:30"]
                else:
                    available_buckets = ["10:30-11:00", "11:00-11:30", "11:30-12:00", "12:00-12:30", "12:30-13:00"]

            default_bucket = [available_buckets[0]] if available_buckets else []
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
        m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)

        with m_col1:
            render_metric_card("Median SD Extension", core_metrics.get("Median SD Extension", "—"))
            if st.button("See SD Extension distribution", key="btn_ext"):
                st.session_state["active_distribution"] = "extension_sd"

        with m_col2:
            render_metric_card("Median Max Retracement", core_metrics.get("Median Max Retracement", "—"))
            if st.button("See Max Retracement distribution", key="btn_ret"):
                st.session_state["active_distribution"] = "max_retracement_sd"

        with m_col3:
            render_metric_card("Median Retracement before HoS/LoS", core_metrics.get("Median Retracement before HoS/LoS", "—"))
            if st.button("See before HoS/LoS distribution", key="btn_hos"):
                st.session_state["active_distribution"] = "retracement_before_extreme_sd"

        with m_col4:
            render_metric_card("Median Retracement after 0.5 SD", core_metrics.get("Median Retracement after 0.5 SD reached", "—"))
            if st.button("See after 0.5 SD distribution", key="btn_05"):
                st.session_state["active_distribution"] = "retracement_after_05_sd"

        with m_col5:
            first_ret_str = core_metrics.get("First Retracement Median Time", "—")
            render_metric_card("Retracement Median Time", first_ret_str)
            if st.button("See Retracement Time distribution", key="btn_retrace_time"):
                st.session_state["active_distribution"] = "max_retracement_time"

        with m_col6:
            render_metric_card("Max Extension Median Time", core_metrics.get("Max Extension Median Time", "—"))
            if st.button("See Extension Time distribution", key="btn_ext_time"):
                st.session_state["active_distribution"] = "extension_time"

        active_dist_field = st.session_state.get("active_distribution", "extension_sd")
        titles = {
            "extension_sd": "SD Max Extension - Distribution",
            "max_retracement_sd": "Maximum Retracement - Distribution (Including Negative Values)",
            "retracement_before_extreme_sd": "Retracement Before HoS/LoS - Distribution",
            "retracement_after_05_sd": "Retracement After 0.5 SD Reached - Distribution",
            "max_retracement_time": "Maximum Retracement Clock Time - 30-Minute Distribution",
            "extension_time": "Maximum Extension Peak Clock Time - 30-Minute Distribution",
        }
        dist_title = titles.get(active_dist_field, "Distribution")

        # Distribution Chart with Modal Cluster Highlighting & Negative / Time Support
        if not filtered_events.empty and active_dist_field in filtered_events.columns:
            if active_dist_field in ["max_retracement_time", "extension_time", "first_retracement_time"]:
                time_dist_df = build_time_bucket_distribution(filtered_events, time_col=active_dist_field, range_type=range_type)
                if not time_dist_df.empty:
                    top_count = time_dist_df["count"].max()
                    colors = [TEAL_PRIMARY if c == top_count else "#222930" for c in time_dist_df["count"]]

                    fig = go.Figure()
                    fig.add_trace(
                        go.Bar(
                            x=time_dist_df["time_bucket"],
                            y=time_dist_df["count"],
                            marker=dict(color=colors, line=dict(color=TEAL_PRIMARY, width=0.5)),
                            hovertemplate="<b>Window: %{x} ET</b><br>Sessions: %{y:,}<br>Share: %{customdata}%<extra></extra>",
                            customdata=time_dist_df["percentage"],
                        )
                    )
                    fig.update_layout(
                        title=dict(
                            text=f"<b>{dist_title}</b> (N = {time_dist_df['count'].sum():,} sessions | Highlighted = Peak Time Window)",
                            font=dict(color=TEXT_PRIMARY, size=13.5),
                            x=0.5,
                            xanchor="center",
                            y=0.98,
                        ),
                        template="plotly_dark",
                        paper_bgcolor=BG_DARK,
                        plot_bgcolor=BG_DARK,
                        height=380,
                        margin=dict(l=20, r=20, t=40, b=40),
                        bargap=0.15,
                        xaxis=dict(title=dict(text="Time Window (America/New_York)", font=dict(color=TEXT_MUTED, size=11)), tickfont=dict(color=TEXT_MUTED, size=10), showgrid=False),
                        yaxis=dict(title=dict(text="Session Count", font=dict(color=TEXT_MUTED, size=11)), tickfont=dict(color=TEXT_PRIMARY, size=10), gridcolor="#1B2026", showgrid=True),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No timing records found for this selection.")
            else:
                plot_series = filtered_events[active_dist_field].dropna()
                if not plot_series.empty:
                    if active_dist_field == "extension_sd":
                        edge_points = [round(i * 0.20, 2) for i in range(25)]
                        bins = [-np.inf] + edge_points[1:] + [np.inf]
                        labels = [f"{pt:.2f}" for pt in edge_points[:-1]] + ["4.80+"]
                    else:
                        # Retracements: span negative bins (-0.8 to +2.6)
                        edge_points = [round(i * 0.20 - 0.80, 2) for i in range(18)]
                        bins = [-np.inf] + edge_points[1:] + [np.inf]
                        labels = [f"{pt:.2f}" for pt in edge_points[:-1]] + ["2.60+"]

                    binned = pd.cut(plot_series, bins=bins, labels=labels, right=False)
                    counts_df = binned.value_counts(sort=False).reset_index()
                    counts_df.columns = ["bin", "count"]
                    counts_df["percentage"] = (counts_df["count"] / len(plot_series) * 100).round(1)

                    # Find modal cluster (top 20% frequency bins) to highlight in vibrant teal
                    top_count = counts_df["count"].max()
                    threshold = top_count * 0.70
                    colors = [TEAL_PRIMARY if c >= threshold and c > 0 else "#222930" for c in counts_df["count"]]

                    fig = go.Figure()
                    fig.add_trace(
                        go.Bar(
                            x=counts_df["bin"],
                            y=counts_df["count"],
                            marker=dict(color=colors, line=dict(color=TEAL_PRIMARY, width=0.5)),
                            hovertemplate="<b>Level: %{x} SD</b><br>Frequency: %{y:,} days<br>Share: %{customdata}%<extra></extra>",
                            customdata=counts_df["percentage"],
                        )
                    )
                    fig.update_layout(
                        title=dict(
                            text=f"<b>{dist_title}</b> (N = {len(plot_series):,} sessions | Highlighted = Modal Cluster Target Zone)",
                            font=dict(color=TEXT_PRIMARY, size=13.5),
                            x=0.5,
                            xanchor="center",
                            y=0.98,
                        ),
                        template="plotly_dark",
                        paper_bgcolor=BG_DARK,
                        plot_bgcolor=BG_DARK,
                        height=380,
                        margin=dict(l=20, r=20, t=40, b=40),
                        bargap=0.15,
                        xaxis=dict(title=dict(text="Standard Deviation Units (SD = IDR Range)", font=dict(color=TEXT_MUTED, size=11)), tickfont=dict(color=TEXT_MUTED, size=10), showgrid=False),
                        yaxis=dict(title=dict(text="Session Count", font=dict(color=TEXT_MUTED, size=11)), tickfont=dict(color=TEXT_PRIMARY, size=10), gridcolor="#1B2026", showgrid=True),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No numerical observations available for this metric under current filters.")

            # DR Drive Playbook & Execution Insight Card
            med_ext_val = core_metrics.get("Median SD Extension", "—")
            med_ret_val = core_metrics.get("Median Max Retracement", "—")
            first_ret_time_val = core_metrics.get("First Retracement Median Time", "—")
            max_ret_time_val = core_metrics.get("Max Retracement Median Time", "—")
            med_time_val = core_metrics.get("Max Extension Median Time", "—")

            st.markdown(
                f"""
                <div class="hud-box">
                    <div class="hud-title">⚡ DR DRIVE TIME & PRICE CONFLUENCE PLAYBOOK</div>
                    <div class="hud-desc">
                        • <b>Phase 1 (Retracement / Limit Entry Window):</b> Expect price to pull back into the <b>0.60x – {med_ret_val}</b> IDR zone on average between <b>{first_ret_time_val}</b> (first entry fill) and <b>{max_ret_time_val}</b> (deepest retest).<br/>
                        • <b>Phase 2 (Extension / Profit Target Window):</b> Session trend reaches the median extension of <b>{med_ext_val}</b> on average at <b>{med_time_val}</b>. Low-hanging fruit target = <b>0.50x SD</b>.<br/>
                        • <b>Phase 3 (Time Expiration Decay Warning):</b> If price has not reached {med_ext_val} by <b>{med_time_val}</b>, statistical probability of reaching 1.2x–1.5x SD drops significantly. Scale back targets to 0.5x SD or IDR Mid.<br/>
                        • <b>False Day Playbook:</b> If the DR rule is violated (opposite side close), historical false days reverse to <b>2.0x – 2.5x SD</b> on the opposite side.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No confirmed events matching current granular filters.")

    # ========================================================
    # VIEW 2: LIVE TRADE CALCULATOR & DR DRIVE HUD
    # ========================================================
    elif active_view == "Trade Calculator":
        st.markdown("### 🧮 Live Session Trade Calculator & Position Sizer")
        st.caption("Input today's active Defining Range to instantly generate exact limit entry prices, profit target tiers, position sizing, and False Day Playbook projections.")

        calc_col1, calc_col2 = st.columns([1.8, 3.2])

        with calc_col1:
            live_instrument = st.selectbox(
                "Trading Contract",
                [
                    "E-mini S&P (ES)", "Micro E-mini S&P (MES)",
                    "Nasdaq 100 (NQ)", "Micro Nasdaq (MNQ)",
                    "Gold Futures (GC)", "Micro Gold (MGC)",
                    "E-mini Dow (YM)", "Micro Dow (MYM)",
                    "Euro FX (6E / EURUSD)",
                ],
                index=0,
            )
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
            elif "MYM" in live_instrument:
                live_sym = "MYM"
            elif "YM" in live_instrument or "Dow" in live_instrument:
                live_sym = "YM"
            elif "Euro" in live_instrument or "6E" in live_instrument:
                live_sym = "6E"
            else:
                live_sym = "ES"

            direction_input = st.radio("Confirmation Direction", ["LONG ↗", "SHORT ↘"], index=0, horizontal=True)
            active_dir = "LONG" if "LONG" in direction_input else "SHORT"

            if "GC" in live_sym or "MGC" in live_sym:
                default_high, default_low = 2750.0, 2735.0
            elif "NQ" in live_sym or "MNQ" in live_sym:
                default_high, default_low = 20150.0, 20080.0
            elif "YM" in live_sym or "MYM" in live_sym:
                default_high, default_low = 41250.0, 41100.0
            elif "6E" in live_sym:
                default_high, default_low = 1.0850, 1.0820
            else:
                default_high, default_low = 5520.0, 5500.0

            inp_col1, inp_col2 = st.columns(2)
            with inp_col1:
                input_dr_high = st.number_input("DR High", value=default_high, step=1.0 if "6E" not in live_sym else 0.0005, format="%.2f" if "6E" not in live_sym else "%.4f")
            with inp_col2:
                input_dr_low = st.number_input("DR Low", value=default_low, step=1.0 if "6E" not in live_sym else 0.0005, format="%.2f" if "6E" not in live_sym else "%.4f")

            st.markdown("#### 2. Execution Strategy")
            entry_model = st.selectbox(
                "Limit Entry Level",
                [
                    "75% Retracement (0.75x Retracement)",
                    "80% Retracement (0.80x Retracement)",
                    "Mid-DR (0.50x Retracement)",
                    "25% Retracement (0.25x Retracement)",
                    "DR Boundary (0.00x Retracement)",
                ],
                index=0,
            )
            entry_sd_map = {
                "75% Retracement (0.75x Retracement)": 0.75,
                "80% Retracement (0.80x Retracement)": 0.80,
                "Mid-DR (0.50x Retracement)": 0.50,
                "25% Retracement (0.25x Retracement)": 0.25,
                "DR Boundary (0.00x Retracement)": 0.00,
            }
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
                render_metric_card("Entry Order", f"{plan.entry_price:.2f}" if "6E" not in live_sym else f"{plan.entry_price:.4f}")
            with p_col2:
                render_metric_card("Invalidation Stop", f"{plan.stop_price:.2f}" if "6E" not in live_sym else f"{plan.stop_price:.4f}")
            with p_col3:
                render_metric_card("Stop Distance", f"{plan.stop_distance_pts:.2f} pts" if "6E" not in live_sym else f"{plan.stop_distance_pts:.4f}")
            with p_col4:
                render_metric_card("Position Size", f"{plan.contracts} Contract(s)")

            st.markdown("#### Take-Profit Tiers & Mathematical Expectations")

            tp_rows = []
            for t in plan.targets:
                tp_rows.append({
                    "Target Tier": t["sd_level"],
                    "Exit Price": f"{t['tp_price']:.2f}" if "6E" not in live_sym else f"{t['tp_price']:.4f}",
                    "Gain (Pts)": f"+{t['gain_pts']:.2f} pts",
                    "Dollar Gain ($)": f"+${t['gain_dollars']:,.2f}",
                    "Risk:Reward": f"1 : {t['rr_ratio']:.2f}",
                })

            st.dataframe(pd.DataFrame(tp_rows), use_container_width=True, hide_index=True)

            st.markdown("#### 🔄 False Day Playbook (Opposite Breakout Scenario)")
            st.dataframe(pd.DataFrame(plan.false_day_targets), use_container_width=True, hide_index=True)

            # Price Map Chart
            fig_map = go.Figure()

            # Target lines
            for t in plan.targets:
                fig_map.add_trace(go.Scatter(
                    x=[0, 1], y=[t["tp_price"], t["tp_price"]],
                    mode="lines+text", name=t["sd_level"],
                    text=["", f"TP {t['sd_level']} ({t['tp_price']}) - 1:{t['rr_ratio']:.1f} R:R"],
                    textposition="middle right",
                    line=dict(color=TEAL_LIGHT if t["sd_val"] <= 0.5 else "#00C896", width=1, dash="dot"),
                ))

            # Entry line
            fig_map.add_trace(go.Scatter(
                x=[0, 1], y=[plan.entry_price, plan.entry_price],
                mode="lines+text", name="Entry",
                text=["", f"★ ENTRY ({plan.entry_price})"],
                textposition="middle right",
                line=dict(color=TEAL_PRIMARY, width=3),
            ))

            # Stop line
            fig_map.add_trace(go.Scatter(
                x=[0, 1], y=[plan.stop_price, plan.stop_price],
                mode="lines+text", name="Stop Loss",
                text=["", f"🛑 STOP / INVALIDATION ({plan.stop_price})"],
                textposition="middle right",
                line=dict(color=ACCENT_RED, width=2, dash="dash"),
            ))

            fig_map.update_layout(
                template="plotly_dark",
                paper_bgcolor=BG_DARK,
                plot_bgcolor=BG_DARK,
                height=320,
                showlegend=False,
                margin=dict(l=10, r=220, t=10, b=10),
                xaxis=dict(showticklabels=False, showgrid=False, range=[0, 1.4]),
                yaxis=dict(gridcolor="#1B2026", showgrid=True),
            )
            st.plotly_chart(fig_map, use_container_width=True)

    # ========================================================
    # VIEW 3: SYSTEMATIC STRATEGY BACKTESTER (DR DRIVE ENGINE)
    # ========================================================
    elif active_view == "Strategy Backtester":
        min_year = int(raw_df["trading_date"].dropna().dt.year.min()) if not raw_df.empty else 2010
        max_year = int(raw_df["trading_date"].dropna().dt.year.max()) if not raw_df.empty else 2026
        span_years = max_year - min_year + 1
        st.markdown(f"### 🧪 {span_years}-Year Systematic Strategy Backtester & Simulator")
        st.caption(f"Simulate rule-based DR execution across {len(raw_df):,} historical sessions ({min_year}–{max_year}). Test DR Drive 75% retracement setups, stop loss variations, and take-profit tiers.")

        bt_settings_col1, bt_settings_col2, bt_settings_col3, bt_settings_col4 = st.columns(4)

        with bt_settings_col1:
            bt_entry_choice = st.selectbox(
                "Entry Retracement Level",
                ["75% Retracement (0.75x SD)", "80% Retracement (0.80x SD)", "Mid-DR (0.50x SD)", "25% Retracement (0.25x SD)", "DR Level (0.00x SD)"],
                index=0,
            )
            bt_entry_sd = {"75% Retracement (0.75x SD)": 0.75, "80% Retracement (0.80x SD)": 0.80, "Mid-DR (0.50x SD)": 0.50, "25% Retracement (0.25x SD)": 0.25, "DR Level (0.00x SD)": 0.00}[bt_entry_choice]

        with bt_settings_col2:
            bt_stop_choice = st.selectbox("Stop Loss Rule", ["Opposite DR (1.0x SD)", "Mid-DR (0.5x SD)"], index=0)
            bt_stop_sd = 1.0 if "1.0x" in bt_stop_choice else 0.5

        with bt_settings_col3:
            bt_tp_choice = st.selectbox("Take Profit Target", ["0.0x SD (DR Boundary)", "0.5x SD (Low-Hanging Fruit)", "0.8x SD", "1.0x SD", "1.2x SD", "1.5x SD", "2.0x SD"], index=1)
            bt_tp_sd = 0.0 if "0.0x" in bt_tp_choice else (0.5 if "0.5x" in bt_tp_choice else float(bt_tp_choice.split()[0].replace("x", "")))

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
            render_metric_card("Total Filled Trades", f"{bt_res.filled_trades:,}")
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

        # Trade Outcome Distribution Breakdown
        b_col1, b_col2, b_col3, b_col4 = st.columns(4)
        with b_col1:
            st.metric("✅ Winning Trades", f"{bt_res.winning_trades:,}")
        with b_col2:
            st.metric("❌ Losing Trades", f"{bt_res.losing_trades:,}")
        with b_col3:
            st.metric("⚪ Neutral (Break-even)", f"{bt_res.neutral_trades:,}")
        with b_col4:
            st.metric("📈 Cumulative R Return", f"+{bt_res.total_r_return:.1f} R")

        st.markdown("#### 📈 15-Year Cumulative Equity Curve")
        if not bt_res.equity_curve.empty:
            fig_equity = px.line(
                bt_res.equity_curve,
                x="trading_date",
                y="equity",
                title=f"Portfolio Equity Curve Over 15 Years (Starting Balance: $25,000, Risk: 1% / trade)",
            )
            fig_equity.update_traces(line_color=TEAL_PRIMARY, line_width=1.5)
            fig_equity.update_layout(
                template="plotly_dark",
                paper_bgcolor=BG_DARK,
                plot_bgcolor=BG_DARK,
                height=380,
                xaxis=dict(title="Date", gridcolor="#1B2026"),
                yaxis=dict(title="Account Balance ($)", gridcolor="#1B2026"),
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
            edge_entry_choice = st.selectbox("Entry Retracement Model", ["75% Retracement (0.75x)", "Mid-DR (0.50x Retracement)", "DR Level (0.00x)", "25% Retracement (0.25x)"], index=1)
            edge_entry_sd = 0.75 if "0.75x" in edge_entry_choice else (0.5 if "0.50x" in edge_entry_choice else (0.0 if "0.00x" in edge_entry_choice else 0.25))

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
                xaxis=dict(title="Target SD Level", gridcolor="#1B2026"),
                yaxis=dict(title="Probability (%)", side="left", gridcolor="#1B2026", range=[0, 100]),
                yaxis2=dict(title="Expected Value (R / trade)", side="right", overlaying="y", showgrid=False),
                legend=dict(x=0.75, y=0.95),
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
    # VIEW 6: TIMING & RETRACEMENT TIME MATRIX
    # ========================================================
    elif active_view == "Timing Heatmap":
        st.markdown("### ⏰ Retracement Depth & Session Timing Heatmap Engine")
        st.caption(f"Analyze the exact relationship between retracement depths (0.2x, 0.5x, 0.8x) and clock time intervals for {range_type} sessions.")

        t_tab1, t_tab2, t_tab3 = st.tabs([
            "🕒 Retracement Depth vs. Time Matrix",
            "⏱️ Maximum Retracement Time Distribution",
            "📅 Day-of-Week vs. Confirmation Matrix",
        ])

        with t_tab1:
            st.markdown("#### 🎯 Retracement Depth vs. 30-Minute Time Window Matrix")
            st.caption("Answers: *'At what time of day does a 0.2x, 0.5x, 0.8x, or 1.0x retracement occur across the session?'*")

            t_ctrl1, t_ctrl2 = st.columns(2)
            with t_ctrl1:
                selected_time_metric = st.radio(
                    "Retracement Reference",
                    ["Maximum Retracement Time", "First Retracement Time"],
                    index=0,
                    horizontal=True,
                )
                time_col_key = "max_retracement_time" if selected_time_metric == "Maximum Retracement Time" else "first_retracement_time"

            with t_ctrl2:
                matrix_display_mode = st.radio(
                    "Display Metric",
                    ["Session Counts", "Percentage Share (%)"],
                    index=0,
                    horizontal=True,
                )

            matrix_df = build_retracement_time_matrix(
                raw_df,
                range_type=range_type,
                time_col=time_col_key,
                instrument=instrument,
            )

            if not matrix_df.empty:
                plot_matrix = matrix_df.copy()
                if matrix_display_mode == "Percentage Share (%)":
                    total_events = plot_matrix.sum().sum()
                    if total_events > 0:
                        plot_matrix = (plot_matrix / total_events * 100).round(1)

                fig_matrix = px.imshow(
                    plot_matrix,
                    labels=dict(x="30-Minute Time Window (America/New_York)", y="Retracement Depth Tier", color="Share (%)" if "%" in matrix_display_mode else "Sessions"),
                    color_continuous_scale="Tealgrn",
                    aspect="auto",
                    title=f"<b>Retracement Depth vs. {selected_time_metric} ({range_type} | {instrument})</b>",
                )
                fig_matrix.update_layout(
                    template="plotly_dark",
                    paper_bgcolor=BG_DARK,
                    plot_bgcolor=BG_DARK,
                    height=400,
                    margin=dict(l=20, r=20, t=50, b=30),
                    xaxis=dict(tickfont=dict(color=TEXT_PRIMARY, size=10)),
                    yaxis=dict(tickfont=dict(color=TEXT_PRIMARY, size=10)),
                )
                st.plotly_chart(fig_matrix, use_container_width=True)

                st.markdown("##### 📋 Exact Breakdown Data Table")
                st.dataframe(
                    plot_matrix.style.format("{:,.1f}%" if "%" in matrix_display_mode else "{:,.0f}"),
                    use_container_width=True,
                )

                # Summary Insight Box
                st.markdown(
                    f"""
                    <div class="hud-box">
                        <div class="hud-title">💡 RETRACEMENT TIMING CONFLUENCE INSIGHT</div>
                        <div class="hud-desc">
                            • <b>Fast Retracements (0.0x – 0.4x):</b> Frequently occur in the first 30–60 minutes following the Defining Range close.<br/>
                            • <b>Deep Retracements (0.6x – 0.8x IDR):</b> Cluster heavily in the mid-session consolidation window before the session extension.<br/>
                            • <b>False Day Breaches (>1.0x SD):</b> Concentrated later in the session when initial directional structure fails.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("No timing records available for the selected range and instrument.")

        with t_tab2:
            st.markdown("#### ⏱️ Maximum Retracement & Extension Chronological Distributions")
            st.caption("Chronological distribution of when the deepest session pullbacks and session extremes occur.")

            ret_dist_col1, ret_dist_col2 = st.columns(2)

            with ret_dist_col1:
                st.markdown("##### 🔻 Maximum Retracement Time Distribution")
                max_ret_dist = build_time_bucket_distribution(raw_df, time_col="max_retracement_time", range_type=range_type, instrument=instrument)
                if not max_ret_dist.empty:
                    top_c = max_ret_dist["count"].max()
                    cols = [TEAL_PRIMARY if c == top_c else "#222930" for c in max_ret_dist["count"]]
                    fig_r = go.Figure(go.Bar(
                        x=max_ret_dist["time_bucket"],
                        y=max_ret_dist["count"],
                        marker=dict(color=cols, line=dict(color=TEAL_PRIMARY, width=0.5)),
                        hovertemplate="<b>Window: %{x}</b><br>Count: %{y:,}<br>Share: %{customdata}%<extra></extra>",
                        customdata=max_ret_dist["percentage"],
                    ))
                    fig_r.update_layout(
                        template="plotly_dark",
                        paper_bgcolor=BG_DARK,
                        plot_bgcolor=BG_DARK,
                        height=350,
                        margin=dict(l=10, r=10, t=30, b=30),
                        xaxis=dict(title="Time Window (ET)", tickfont=dict(color=TEXT_MUTED, size=9)),
                        yaxis=dict(title="Sessions", tickfont=dict(color=TEXT_PRIMARY, size=9)),
                    )
                    st.plotly_chart(fig_r, use_container_width=True)
                else:
                    st.info("No data.")

            with ret_dist_col2:
                st.markdown("##### 🔺 Max Extension (HoS/LoS) Time Distribution")
                ext_dist = build_time_bucket_distribution(raw_df, time_col="extension_time", range_type=range_type, instrument=instrument)
                if not ext_dist.empty:
                    top_c = ext_dist["count"].max()
                    cols = [ACCENT_BLUE if c == top_c else "#222930" for c in ext_dist["count"]]
                    fig_e = go.Figure(go.Bar(
                        x=ext_dist["time_bucket"],
                        y=ext_dist["count"],
                        marker=dict(color=cols, line=dict(color=ACCENT_BLUE, width=0.5)),
                        hovertemplate="<b>Window: %{x}</b><br>Count: %{y:,}<br>Share: %{customdata}%<extra></extra>",
                        customdata=ext_dist["percentage"],
                    ))
                    fig_e.update_layout(
                        template="plotly_dark",
                        paper_bgcolor=BG_DARK,
                        plot_bgcolor=BG_DARK,
                        height=350,
                        margin=dict(l=10, r=10, t=30, b=30),
                        xaxis=dict(title="Time Window (ET)", tickfont=dict(color=TEXT_MUTED, size=9)),
                        yaxis=dict(title="Sessions", tickfont=dict(color=TEXT_PRIMARY, size=9)),
                    )
                    st.plotly_chart(fig_e, use_container_width=True)
                else:
                    st.info("No data.")

        with t_tab3:
            st.markdown("#### 📅 Confirmation Window vs. Day of Week Heatmap")
            st.caption(f"Identify peak confirmation windows across the trading week for {range_type} sessions.")

            heat_df = build_hos_los_heatmap_data(raw_df, range_type=range_type)
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
                "retracement_before_extreme_sd": "Retracement Before HoS/LoS (SD)",
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

