import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# DR LENS TIME ANALYSIS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
DATABASE_DIR = ROOT / "database"
DISTRIBUTIONS_DIR = DATABASE_DIR / "distributions"
INPUT_FILE = DATABASE_DIR / "events_2024.csv"

DISTRIBUTIONS_DIR.mkdir(parents=True, exist_ok=True)

print("Loading events database for time analysis...")
df = pd.read_csv(INPUT_FILE)
df = df[df["confirmed"] == True].copy()
print(f"Loaded {len(df):,} confirmed events.")

# Datetime conversions
df["confirmation_time"] = pd.to_datetime(df["confirmation_time"], errors="coerce")
df["max_retracement_time"] = pd.to_datetime(df["max_retracement_time"], errors="coerce")
df["extension_time"] = pd.to_datetime(df["extension_time"], errors="coerce")

# 15-min Confirmation Bucket
def bucket_15m(ts):
    if pd.isna(ts):
        return None
    h = ts.hour
    m = (ts.minute // 15) * 15
    start_min = h * 60 + m
    end_min = (start_min + 15) % 1440
    return f"{start_min // 60:02d}:{start_min % 60:02d}–{end_min // 60:02d}:{end_min % 60:02d}"

# 30-min Confirmation Bucket
def bucket_30m(ts):
    if pd.isna(ts):
        return None
    h = ts.hour
    m = (ts.minute // 30) * 30
    start_min = h * 60 + m
    end_min = (start_min + 30) % 1440
    return f"{start_min // 60:02d}:{start_min % 60:02d}-{end_min // 60:02d}:{end_min % 60:02d}"

df["conf_15m"] = df["confirmation_time"].apply(bucket_15m)
df["conf_30m"] = df["confirmation_time"].apply(bucket_30m)

# 1. Confirmation 15-min distribution
conf_15 = df["conf_15m"].value_counts().reset_index()
conf_15.columns = ["bucket", "count"]
conf_15["percentage"] = (conf_15["count"] / len(df) * 100).round(2)
conf_15.to_csv(DISTRIBUTIONS_DIR / "confirmation_time_15min_distribution.csv", index=False)

# 2. Maximum Extension Time Distribution (1-hour buckets)
ext_hours = df["extension_time"].dropna().dt.hour
ext_dist = ext_hours.value_counts().sort_index().reset_index()
ext_dist.columns = ["hour", "count"]
ext_dist["extension_hour_bucket"] = ext_dist["hour"].apply(lambda h: f"{int(h):02d}:00–{(int(h)+1)%24:02d}:00")
ext_dist["percentage"] = (ext_dist["count"] / len(df) * 100).round(2)
ext_dist.to_csv(DISTRIBUTIONS_DIR / "maximum_extension_time_distribution.csv", index=False)

# 3. Median Extension Time by Range and Direction
med_summary = df.groupby(["range_type", "direction"]).agg(
    count=("confirmation_time", "count"),
    median_ext_sd=("extension_sd", "median"),
    median_ret_sd=("max_retracement_sd", "median"),
).reset_index()
med_summary.to_csv(DISTRIBUTIONS_DIR / "median_extension_time_range_direction.csv", index=False)

print("Time analysis completed successfully.")