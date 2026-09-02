import pandas as pd
from pathlib import Path

# ============================================================
# SETTINGS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
FILE_PATH = ROOT / "data" / "DAT_ASCII_NSXUSD_M1_2024.csv"
OUTPUT_FILE = ROOT / "database" / "ranges_2024.csv"

# ============================================================
# LOAD M1 DATA
# ============================================================

columns = ["datetime", "open", "high", "low", "close", "volume"]
m1 = pd.read_csv(FILE_PATH, sep=";", header=None, names=columns)
m1["datetime"] = pd.to_datetime(m1["datetime"], format="%Y%m%d %H%M%S")

for col in ["open", "high", "low", "close", "volume"]:
    m1[col] = pd.to_numeric(m1[col], errors="coerce")

m1 = m1.dropna().sort_values("datetime").set_index("datetime")

# ============================================================
# M1 → M5
# ============================================================

m5 = m1.resample("5min").agg({
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum",
}).dropna()

m5["body_high"] = m5[["open", "close"]].max(axis=1)
m5["body_low"] = m5[["open", "close"]].min(axis=1)

# ============================================================
# RANGE DEFINITIONS
# ============================================================

SESSIONS = {
    "ADR": {"start": "19:30", "end": "20:30", "prev_day": True},
    "ODR": {"start": "03:00", "end": "04:00", "prev_day": False},
    "RDR": {"start": "09:30", "end": "10:30", "prev_day": False},
}

trading_dates = sorted(
    pd.Series((m5.index - pd.Timedelta(hours=18)).date).unique()
)

results = []

for trading_date in trading_dates:
    t_date_str = str(trading_date)
    prev_date_str = str((pd.Timestamp(trading_date) - pd.Timedelta(days=1)).date())

    for range_name, cfg in SESSIONS.items():
        r_date = prev_date_str if cfg["prev_day"] else t_date_str
        start_ts = pd.Timestamp(f"{r_date} {cfg['start']}:00")
        end_ts = pd.Timestamp(f"{r_date} {cfg['end']}:00")

        range_data = m5.loc[(m5.index >= start_ts) & (m5.index < end_ts)]

        if len(range_data) != 12:
            continue

        dr_high = float(range_data["body_high"].max())
        dr_low = float(range_data["body_low"].min())
        idr_high = float(range_data["high"].max())
        idr_low = float(range_data["low"].min())

        results.append({
            "trading_date": t_date_str,
            "range_type": range_name,
            "dr_high": dr_high,
            "dr_low": dr_low,
            "dr_range": dr_high - dr_low,
            "idr_high": idr_high,
            "idr_low": idr_low,
            "idr_range": idr_high - idr_low,
        })

ranges_df = pd.DataFrame(results).sort_values(["trading_date", "range_type"]).reset_index(drop=True)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
ranges_df.to_csv(OUTPUT_FILE, index=False)

print(f"Generated {len(ranges_df):,} ranges. Saved to {OUTPUT_FILE}")