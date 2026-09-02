import pandas as pd
from dashboard import (
    normalize_columns,
    filter_data,
    calc_overview_kpis,
    calc_core_metrics,
    make_15m_bucket,
    make_30m_bucket,
)


def test_bucket():
    assert make_15m_bucket(0) == "00:00–00:15"
    assert make_15m_bucket(255) == "04:15–04:30"
    assert make_15m_bucket(1425) == "23:45–00:00"
    assert make_30m_bucket("2024-01-01 20:35:00") == "20:30-21:00"
    assert make_30m_bucket("2024-01-01 04:15:00") == "04:00-04:30"


def test_filters_and_metrics():
    df = pd.DataFrame({
        "instrument": ["NQ", "NQ", "ES"],
        "trading_date": ["2024-01-01", "2024-01-02", "2025-01-01"],
        "day_of_week": ["Monday", "Tuesday", "Wednesday"],
        "range_type": ["ADR", "RDR", "ADR"],
        "confirmed": [True, True, True],
        "direction": ["LONG", "SHORT", "LONG"],
        "confirmation_time": ["2024-01-01 10:30", "2024-01-02 10:45", "2025-01-01 04:00"],
        "dr_rule_true": [True, False, True],
        "retraced_into_dr": [True, True, False],
        "outside_dr_closed": [True, False, False],
        "extension_sd": [1.0, 2.0, 3.0],
        "max_retracement_sd": [0.4, 0.8, 1.0],
        "retracement_before_extreme_sd": [0.1, 0.2, 0.3],
        "retracement_after_05_sd": [0.3, 0.5, 0.6],
        "mean_sd_up": [1.0, 0.5, 3.0],
        "mean_sd_down": [0.2, 2.0, 0.1],
    })
    df = normalize_columns(df)
    out = filter_data(df, instrument="NQ", day_filter="Monday", range_type="ADR", direction="LONG")
    assert len(out) == 1
    
    kpis = calc_overview_kpis(out, out)
    assert kpis["Conf. Long (%)"] == "100.0%"
    assert kpis["DR true (%)"] == "100.0%"
    
    core = calc_core_metrics(out)
    assert core["Median SD Extension"] == "1.0x"
    assert core["Median Max Retracement"] == "0.4x"


if __name__ == "__main__":
    test_bucket()
    test_filters_and_metrics()
    print("PASS: all dashboard tests passed successfully!")
