"""
Analytics Engine for DR Lens Platform
Provides quantitative models for:
1. Live Session Trade Calculator & Position Planner
2. 15-Year Strategy Backtester & Equity Curve Simulator
3. Cumulative Probability & Expected Value (EV) Optimizer
4. Inter-Session Confluence Matrix (ADR -> ODR -> RDR)
5. HOD / LOD Intraday Timing Heatmaps
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# POINT VALUES & CONTRACT SPECIFICATIONS
# ============================================================

CONTRACT_SPECS: Dict[str, Dict[str, Any]] = {
    "NQ": {"name": "E-mini Nasdaq 100", "point_value": 20.0, "tick_size": 0.25, "is_micro": False},
    "ES": {"name": "E-mini S&P 500", "point_value": 50.0, "tick_size": 0.25, "is_micro": False},
    "MNQ": {"name": "Micro E-mini Nasdaq 100", "point_value": 2.0, "tick_size": 0.25, "is_micro": True},
    "MES": {"name": "Micro E-mini S&P 500", "point_value": 5.0, "tick_size": 0.25, "is_micro": True},
}


# ============================================================
# 1. LIVE SESSION TRADE CALCULATOR
# ============================================================

@dataclass
class TradePlan:
    dr_range: float
    direction: str
    entry_label: str
    entry_price: float
    stop_price: float
    stop_distance_pts: float
    risk_dollars: float
    contracts: int
    targets: List[Dict[str, Any]]
    historical_win_rate: float
    expected_value_dollars: float


def calculate_trade_plan(
    dr_high: float,
    dr_low: float,
    direction: str,
    entry_retrace_sd: float = 0.5,  # 0.0 = DR boundary, 0.5 = Mid-DR
    stop_loss_sd: float = 1.0,      # 1.0 = Opposite DR
    instrument: str = "NQ",
    account_size: float = 25000.0,
    risk_pct: float = 1.0,
    historical_stats: Optional[Dict[str, float]] = None,
) -> TradePlan:
    """
    Computes exact prices, contract sizing, R:R ratios, and target levels for a live trade setup.
    """
    dr_range = max(0.25, dr_high - dr_low)
    direction_upper = direction.upper()

    # Retracement Entry Price
    if direction_upper == "LONG":
        entry_price = dr_high - (entry_retrace_sd * dr_range)
        stop_price = dr_high - (stop_loss_sd * dr_range)
    else:  # SHORT
        entry_price = dr_low + (entry_retrace_sd * dr_range)
        stop_price = dr_low + (stop_loss_sd * dr_range)

    stop_distance_pts = max(0.25, abs(entry_price - stop_price))

    # Contract Specifications
    spec = CONTRACT_SPECS.get(instrument, CONTRACT_SPECS["NQ"])
    point_value = spec["point_value"]

    # Position Sizing
    risk_dollars = account_size * (risk_pct / 100.0)
    risk_per_contract = stop_distance_pts * point_value
    contracts = max(1, int(math.floor(risk_dollars / risk_per_contract)))
    actual_risk = contracts * risk_per_contract

    # Target Tiers
    target_tiers_sd = [0.2, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0]
    targets: List[Dict[str, Any]] = []

    for sd in target_tiers_sd:
        if direction_upper == "LONG":
            tp_price = dr_high + (sd * dr_range)
        else:
            tp_price = dr_low - (sd * dr_range)

        gain_pts = abs(tp_price - entry_price)
        gain_dollars = gain_pts * point_value * contracts
        rr_ratio = gain_pts / stop_distance_pts if stop_distance_pts > 0 else 0.0

        targets.append({
            "sd_level": f"{sd:.1f}x SD",
            "sd_val": sd,
            "tp_price": round(tp_price, 2),
            "gain_pts": round(gain_pts, 2),
            "gain_dollars": round(gain_dollars, 2),
            "rr_ratio": round(rr_ratio, 2),
        })

    # Historical win rate approximation from provided stats or baseline
    win_rate = historical_stats.get("win_rate_05", 81.0) if historical_stats else 81.0
    ev_dollars = ((win_rate / 100.0) * targets[1]["gain_dollars"]) - ((1 - (win_rate / 100.0)) * actual_risk)

    entry_labels = {
        0.0: "DR Level (0.0x)",
        0.25: "25% Retracement (0.25x)",
        0.5: "Mid-DR (0.50x)",
        0.75: "75% Retracement (0.75x)",
        1.0: "Opposite DR (1.00x)",
    }
    entry_label = entry_labels.get(round(entry_retrace_sd, 2), f"{entry_retrace_sd:.2f}x SD")

    return TradePlan(
        dr_range=round(dr_range, 2),
        direction=direction_upper,
        entry_label=entry_label,
        entry_price=round(entry_price, 2),
        stop_price=round(stop_price, 2),
        stop_distance_pts=round(stop_distance_pts, 2),
        risk_dollars=round(actual_risk, 2),
        contracts=contracts,
        targets=targets,
        historical_win_rate=round(win_rate, 1),
        expected_value_dollars=round(ev_dollars, 2),
    )


# ============================================================
# 2. 15-YEAR STRATEGY BACKTESTER
# ============================================================

@dataclass
class BacktestResult:
    total_events: int
    filled_trades: int
    winning_trades: int
    losing_trades: int
    fill_rate_pct: float
    win_rate_pct: float
    profit_factor: float
    total_pnl_dollars: float
    total_r_return: float
    max_drawdown_dollars: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trade_log: pd.DataFrame
    equity_curve: pd.DataFrame
    monthly_pnl_matrix: pd.DataFrame


def run_strategy_backtest(
    df: pd.DataFrame,
    entry_retrace_sd: float = 0.5,       # 0.0 = DR Level, 0.5 = Mid-DR, etc.
    stop_loss_sd: float = 1.0,           # 1.0 = Opposite DR
    take_profit_sd: float = 0.8,         # 0.5, 0.8, 1.0, 1.2, 1.5
    account_size: float = 25000.0,
    risk_pct_per_trade: float = 1.0,
    early_time_filter_only: bool = False,
    instrument: str = "All",
    range_type: str = "All",
) -> BacktestResult:
    """
    Backtests a systematic DR Retracement rule over historical event records.
    """
    if df.empty:
        empty_df = pd.DataFrame()
        return BacktestResult(
            total_events=0, filled_trades=0, winning_trades=0, losing_trades=0,
            fill_rate_pct=0.0, win_rate_pct=0.0, profit_factor=0.0, total_pnl_dollars=0.0,
            total_r_return=0.0, max_drawdown_dollars=0.0, max_drawdown_pct=0.0, sharpe_ratio=0.0,
            trade_log=empty_df, equity_curve=empty_df, monthly_pnl_matrix=empty_df
        )

    # Filter confirmed events
    sample = df[df["confirmed"] == True].copy()

    if instrument not in ["All", "All Instruments"] and "instrument" in sample.columns:
        sample = sample[sample["instrument"] == instrument]

    if range_type not in ["All", "All Ranges"] and "range_type" in sample.columns:
        sample = sample[sample["range_type"] == range_type]

    if early_time_filter_only and "conf_30m_bucket" in sample.columns:
        early_buckets = ["20:30-21:00", "04:00-04:30", "10:30-11:00"]
        sample = sample[sample["conf_30m_bucket"].isin(early_buckets)]

    sample = sample.sort_values("trading_date").reset_index(drop=True)

    risk_dollars = account_size * (risk_pct_per_trade / 100.0)
    # Risk-to-reward ratio for this setup
    risk_distance_sd = max(0.1, stop_loss_sd - entry_retrace_sd)
    reward_distance_sd = take_profit_sd + entry_retrace_sd
    trade_rr = reward_distance_sd / risk_distance_sd

    trades: List[Dict[str, Any]] = []

    for _, row in sample.iterrows():
        max_ret = row.get("max_retracement_sd", 0.0)
        max_ext = row.get("extension_sd", 0.0)
        dr_true = row.get("dr_rule_true", False)
        ret_before_ext = row.get("retracement_before_extreme_sd", 0.0)

        # 1. Check if limit entry was filled
        # For entry_retrace_sd == 0.0, any retraced_into_dr == True fills it.
        # Otherwise, max_ret >= entry_retrace_sd is required.
        was_filled = (max_ret >= entry_retrace_sd) if entry_retrace_sd > 0 else True

        if not was_filled:
            continue

        # 2. Check outcome
        # If DR Rule is True, price never broke the opposite DR (1.0x SD).
        # If stop_loss_sd == 1.0, DR True ensures stop was never violated.
        # If stop_loss_sd < 1.0 (e.g. 0.5 SD), check if max_ret >= stop_loss_sd.
        stopped_out = (max_ret >= stop_loss_sd) if stop_loss_sd < 1.0 else (not dr_true)

        # Reached target?
        target_reached = max_ext >= take_profit_sd

        # If DR True and reached target => Win
        # If DR False, did it reach target before extreme / stop?
        if dr_true and target_reached:
            is_win = True
        elif not stopped_out and target_reached:
            is_win = True
        elif not dr_true and target_reached and (ret_before_ext < stop_loss_sd):
            is_win = True
        else:
            is_win = False

        r_pnl = trade_rr if is_win else -1.0
        dollar_pnl = risk_dollars * r_pnl

        t_date = row.get("trading_date")
        trades.append({
            "trading_date": t_date,
            "year": t_date.year if pd.notnull(t_date) else None,
            "month": t_date.month if pd.notnull(t_date) else None,
            "instrument": row.get("instrument", "NQ"),
            "range_type": row.get("range_type", "ADR"),
            "direction": row.get("direction", "LONG"),
            "dr_true": dr_true,
            "max_ret_sd": round(max_ret, 2),
            "max_ext_sd": round(max_ext, 2),
            "is_win": is_win,
            "r_pnl": round(r_pnl, 2),
            "dollar_pnl": round(dollar_pnl, 2),
        })

    trade_log = pd.DataFrame(trades)

    if trade_log.empty:
        empty_df = pd.DataFrame()
        return BacktestResult(
            total_events=len(sample), filled_trades=0, winning_trades=0, losing_trades=0,
            fill_rate_pct=0.0, win_rate_pct=0.0, profit_factor=0.0, total_pnl_dollars=0.0,
            total_r_return=0.0, max_drawdown_dollars=0.0, max_drawdown_pct=0.0, sharpe_ratio=0.0,
            trade_log=empty_df, equity_curve=empty_df, monthly_pnl_matrix=empty_df
        )

    # Equity Curve Calculation
    trade_log["cum_pnl"] = trade_log["dollar_pnl"].cumsum()
    trade_log["cum_r"] = trade_log["r_pnl"].cumsum()
    trade_log["equity"] = account_size + trade_log["cum_pnl"]
    trade_log["peak_equity"] = trade_log["equity"].cummax()
    trade_log["drawdown_dollars"] = trade_log["peak_equity"] - trade_log["equity"]
    trade_log["drawdown_pct"] = (trade_log["drawdown_dollars"] / trade_log["peak_equity"]) * 100.0

    # Summary Metrics
    total_events = len(sample)
    filled_trades = len(trade_log)
    winning_trades = int((trade_log["is_win"] == True).sum())
    losing_trades = filled_trades - winning_trades

    fill_rate_pct = (filled_trades / total_events) * 100.0 if total_events > 0 else 0.0
    win_rate_pct = (winning_trades / filled_trades) * 100.0 if filled_trades > 0 else 0.0

    gross_profit = trade_log.loc[trade_log["dollar_pnl"] > 0, "dollar_pnl"].sum()
    gross_loss = abs(trade_log.loc[trade_log["dollar_pnl"] < 0, "dollar_pnl"].sum())
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

    total_pnl_dollars = trade_log["dollar_pnl"].sum()
    total_r_return = trade_log["r_pnl"].sum()
    max_drawdown_dollars = trade_log["drawdown_dollars"].max()
    max_drawdown_pct = trade_log["drawdown_pct"].max()

    # Sharpe Ratio (annualized based on ~250 trading days)
    returns = trade_log["dollar_pnl"] / account_size
    sharpe = (returns.mean() / returns.std()) * math.sqrt(250) if returns.std() > 0 else 0.0

    # Monthly PnL Matrix (Pivot Table)
    if "year" in trade_log.columns and "month" in trade_log.columns:
        monthly_pnl = trade_log.pivot_table(
            index="year",
            columns="month",
            values="dollar_pnl",
            aggfunc="sum",
            fill_value=0.0,
        )
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly_pnl.columns = [month_names[m - 1] for m in monthly_pnl.columns if 1 <= m <= 12]
        monthly_pnl["Total"] = monthly_pnl.sum(axis=1)
    else:
        monthly_pnl = pd.DataFrame()

    equity_curve = trade_log[["trading_date", "equity", "cum_pnl", "cum_r", "drawdown_pct"]].copy()

    return BacktestResult(
        total_events=total_events,
        filled_trades=filled_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        fill_rate_pct=round(fill_rate_pct, 1),
        win_rate_pct=round(win_rate_pct, 1),
        profit_factor=round(profit_factor, 2),
        total_pnl_dollars=round(total_pnl_dollars, 2),
        total_r_return=round(total_r_return, 1),
        max_drawdown_dollars=round(max_drawdown_dollars, 2),
        max_drawdown_pct=round(max_drawdown_pct, 1),
        sharpe_ratio=round(sharpe, 2),
        trade_log=trade_log,
        equity_curve=equity_curve,
        monthly_pnl_matrix=monthly_pnl,
    )


# ============================================================
# 3. CUMULATIVE PROBABILITY & EXPECTED VALUE OPTIMIZER
# ============================================================

def calc_cumulative_edge_curve(
    confirmed_df: pd.DataFrame,
    entry_retrace_sd: float = 0.5,
    stop_loss_sd: float = 1.0,
) -> pd.DataFrame:
    """
    Calculates the cumulative probability P(Extension >= X) and the resulting
    Expected Value (EV) in R-multiples across standard deviation steps.
    """
    if confirmed_df.empty or "extension_sd" not in confirmed_df.columns:
        return pd.DataFrame()

    # Base on events that filled the entry
    if entry_retrace_sd > 0 and "max_retracement_sd" in confirmed_df.columns:
        valid_sample = confirmed_df[confirmed_df["max_retracement_sd"] >= entry_retrace_sd].copy()
    else:
        valid_sample = confirmed_df.copy()

    if valid_sample.empty:
        return pd.DataFrame()

    total_valid = len(valid_sample)
    sd_steps = np.arange(0.1, 3.1, 0.1)

    rows = []
    risk_r = max(0.1, stop_loss_sd - entry_retrace_sd)

    for sd in sd_steps:
        sd_rounded = round(float(sd), 1)
        # Probability of reaching at least this SD
        reached_count = (valid_sample["extension_sd"] >= sd_rounded).sum()
        prob_win = reached_count / total_valid
        reward_r = sd_rounded + entry_retrace_sd
        rr_ratio = reward_r / risk_r

        # Expected Value in R: P(Win)*Reward - P(Loss)*risk_r
        ev_r = (prob_win * reward_r) - ((1.0 - prob_win) * risk_r)

        rows.append({
            "sd_level": sd_rounded,
            "probability_pct": round(prob_win * 100.0, 1),
            "reward_r": round(reward_r, 2),
            "rr_ratio": round(rr_ratio, 2),
            "expected_value_r": round(ev_r, 2),
            "sample_count": int(reached_count),
        })

    return pd.DataFrame(rows)


# ============================================================
# 4. INTER-SESSION CONFLUENCE MATRIX (ADR -> ODR -> RDR)
# ============================================================

@st.cache_data(show_spinner=False)
def build_inter_session_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups events by trading day to analyze multi-session direction sequences.
    ADR (Asian) -> ODR (London) -> RDR (New York).
    """
    if df.empty or "trading_date" not in df.columns:
        return pd.DataFrame()

    confirmed_only = df[df["confirmed"] == True].copy()
    if confirmed_only.empty:
        return pd.DataFrame()

    # Pivot by trading_date & range_type for direction and extension
    pivot_dir = confirmed_only.pivot_table(
        index=["instrument", "trading_date"],
        columns="range_type",
        values="direction",
        aggfunc="first",
    )

    pivot_ext = confirmed_only.pivot_table(
        index=["instrument", "trading_date"],
        columns="range_type",
        values="extension_sd",
        aggfunc="first",
    )

    merged = pd.DataFrame(index=pivot_dir.index)
    for r in ["ADR", "ODR", "RDR"]:
        if r in pivot_dir.columns:
            merged[f"{r}_dir"] = pivot_dir[r]
        if r in pivot_ext.columns:
            merged[f"{r}_ext"] = pivot_ext[r]

    # Filter complete trading days where ADR, ODR, and RDR confirmed
    complete_days = merged.dropna(subset=["ADR_dir", "ODR_dir", "RDR_dir"]).copy()
    if complete_days.empty:
        return pd.DataFrame()

    complete_days["Sequence"] = complete_days["ADR_dir"] + " → " + complete_days["ODR_dir"] + " → " + complete_days["RDR_dir"]

    # Confluence category
    def classify_sequence(row: pd.Series) -> str:
        a, o, r = row["ADR_dir"], row["ODR_dir"], row["RDR_dir"]
        if a == o == r:
            return "Triple Trend Alignment"
        elif a == o and o != r:
            return "NY Session Reversal"
        elif a != o and o == r:
            return "London Shift & NY Continuation"
        else:
            return "Choppy / Divergent Day"

    complete_days["Category"] = complete_days.apply(classify_sequence, axis=1)

    # Summary table
    seq_summary = complete_days.groupby("Sequence").agg(
        Days=("Category", "count"),
        Category=("Category", "first"),
        Median_NY_Ext=("RDR_ext", lambda x: f"{x.median():.2f}x"),
        Mean_NY_Ext=("RDR_ext", lambda x: f"{x.mean():.2f}x"),
    ).reset_index()

    seq_summary["Share_pct"] = (seq_summary["Days"] / len(complete_days) * 100).round(1)
    seq_summary = seq_summary.sort_values("Days", ascending=False).reset_index(drop=True)

    return seq_summary


# ============================================================
# 5. HOD / LOD TIMING DISTRIBUTION ENGINE
# ============================================================

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


@st.cache_data(show_spinner=False)
def build_hod_lod_heatmap_data(df: pd.DataFrame, range_type: str = "ADR") -> pd.DataFrame:
    """
    Builds a 2D matrix of time intervals vs days of week for session extremes (HoD / LoD).
    """
    if df.empty:
        return pd.DataFrame()

    sample = df.copy()
    if "trading_date" in sample.columns and "day_of_week" not in sample.columns:
        sample["trading_date"] = pd.to_datetime(sample["trading_date"], errors="coerce")
        sample["day_of_week"] = sample["trading_date"].dt.day_name()

    if "confirmation_time" in sample.columns and "conf_30m_bucket" not in sample.columns:
        sample["confirmation_time"] = pd.to_datetime(sample["confirmation_time"], errors="coerce")
        sample["conf_30m_bucket"] = sample["confirmation_time"].apply(make_30m_bucket)

    if range_type not in ["All", "All Ranges"] and "range_type" in sample.columns:
        sample = sample[sample["range_type"] == range_type]

    sample = sample[sample["confirmed"] == True].copy()
    if sample.empty or "conf_30m_bucket" not in sample.columns or "day_of_week" not in sample.columns:
        return pd.DataFrame()

    heatmap = sample.pivot_table(
        index="day_of_week",
        columns="conf_30m_bucket",
        values="confirmed",
        aggfunc="count",
        fill_value=0,
    )

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    return heatmap.reindex([d for d in day_order if d in heatmap.index])
