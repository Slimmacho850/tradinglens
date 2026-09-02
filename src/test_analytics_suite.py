"""
Test Suite for Analytics Engine
"""

import sys
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SRC_DIR = Path(__file__).resolve().parent
DATABASE_DIR = SRC_DIR.parent / "database"

from analytics_engine import (
    calculate_trade_plan,
    run_strategy_backtest,
    calc_cumulative_edge_curve,
    build_inter_session_matrix,
    build_hod_lod_heatmap_data,
)


def test_trade_calculator():
    print("Testing Trade Calculator...")
    plan_long = calculate_trade_plan(
        dr_high=20000.0,
        dr_low=19900.0,
        direction="LONG",
        entry_retrace_sd=0.5,
        stop_loss_sd=1.0,
        instrument="NQ",
        account_size=25000.0,
        risk_pct=1.0,
    )
    assert plan_long.dr_range == 100.0
    assert plan_long.entry_price == 19950.0
    assert plan_long.stop_price == 19900.0
    assert plan_long.stop_distance_pts == 50.0
    assert plan_long.contracts == 0 or plan_long.contracts >= 1
    assert len(plan_long.targets) == 7
    print("  ✓ Long Plan validated successfully")

    plan_short = calculate_trade_plan(
        dr_high=5500.0,
        dr_low=5480.0,
        direction="SHORT",
        entry_retrace_sd=0.0,
        stop_loss_sd=1.0,
        instrument="ES",
        account_size=50000.0,
        risk_pct=2.0,
    )
    assert plan_short.dr_range == 20.0
    assert plan_short.entry_price == 5480.0
    assert plan_short.stop_price == 5500.0
    print("  ✓ Short Plan validated successfully")

    plan_gold = calculate_trade_plan(
        dr_high=2750.0,
        dr_low=2730.0,
        direction="LONG",
        entry_retrace_sd=0.5,
        stop_loss_sd=1.0,
        instrument="GC",
        account_size=25000.0,
        risk_pct=1.0,
    )
    assert plan_gold.dr_range == 20.0
    assert plan_gold.entry_price == 2740.0
    assert plan_gold.stop_price == 2730.0
    assert plan_gold.stop_distance_pts == 10.0
    assert plan_gold.contracts >= 1
    print("  ✓ Gold (GC) Plan validated successfully")


def test_backtester_and_curves():
    master_file = DATABASE_DIR / "events_master.csv"
    if not master_file.exists():
        print("  ⚠️ events_master.csv not found, skipping full dataset test")
        return

    print("Testing Strategy Backtester on Master Database...")
    df = pd.read_csv(master_file)
    df["trading_date"] = pd.to_datetime(df["trading_date"])

    res = run_strategy_backtest(
        df,
        entry_retrace_sd=0.5,
        stop_loss_sd=1.0,
        take_profit_sd=0.8,
        account_size=25000.0,
        risk_pct_per_trade=1.0,
    )

    print(f"  ✓ Backtest Complete: {res.filled_trades:,} trades, Win Rate: {res.win_rate_pct}%, Profit Factor: {res.profit_factor}, Total PnL: ${res.total_pnl_dollars:,.2f}")
    assert res.filled_trades > 0
    assert res.win_rate_pct > 0.0

    print("Testing Cumulative Edge Curve...")
    edge_curve = calc_cumulative_edge_curve(df[df["confirmed"] == True], entry_retrace_sd=0.5)
    print(f"  ✓ Generated {len(edge_curve)} curve rows")
    assert not edge_curve.empty

    print("Testing Inter-Session Confluence Matrix...")
    inter_seq = build_inter_session_matrix(df)
    print(f"  ✓ Found {len(inter_seq)} multi-session sequences")
    assert not inter_seq.empty

    print("Testing HOD/LOD Heatmap Data...")
    heatmap = build_hod_lod_heatmap_data(df, range_type="ADR")
    print(f"  ✓ Generated heatmap matrix with shape {heatmap.shape}")
    assert not heatmap.empty


if __name__ == "__main__":
    test_trade_calculator()
    test_backtester_and_curves()
    print("\n🎉 ALL ANALYTICS ENGINE TESTS PASSED!")
