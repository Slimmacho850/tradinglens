import sys
from pathlib import Path
import pandas as pd
import numpy as np

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ============================================================
# DR LENS STATISTICAL DISTRIBUTION GENERATOR
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
DATABASE_DIR = ROOT / "database"
DISTRIBUTIONS_DIR = DATABASE_DIR / "distributions"
INPUT_FILE = DATABASE_DIR / "events_master.csv" if (DATABASE_DIR / "events_master.csv").exists() else (DATABASE_DIR / "events_2024.csv")

DISTRIBUTIONS_DIR.mkdir(parents=True, exist_ok=True)

print(f"Loading events database from {INPUT_FILE.name} for distribution analysis...")
df = pd.read_csv(INPUT_FILE)
confirmed = df[df["confirmed"] == True].copy()
print(f"Loaded {len(df):,} total records, {len(confirmed):,} confirmed events.")

# Numeric conversions
for col in ["extension_sd", "max_retracement_sd", "retracement_before_extreme_sd", "retracement_after_05_sd"]:
    if col in confirmed.columns:
        confirmed[col] = pd.to_numeric(confirmed[col], errors="coerce")

# 1. Percentiles for SD Extension and Retracements
percentiles = [0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
stats_dict = {
    "Metric": [
        "SD Extension",
        "Max Retracement (SD)",
        "Retracement before HoD/LoD (SD)",
        "Retracement after 0.5 SD (SD)",
    ],
    "Mean": [
        confirmed["extension_sd"].mean(),
        confirmed["max_retracement_sd"].mean(),
        confirmed["retracement_before_extreme_sd"].mean(),
        confirmed["retracement_after_05_sd"].mean(),
    ],
    "Median (50%)": [
        confirmed["extension_sd"].median(),
        confirmed["max_retracement_sd"].median(),
        confirmed["retracement_before_extreme_sd"].median(),
        confirmed["retracement_after_05_sd"].median(),
    ],
    "P25": [
        confirmed["extension_sd"].quantile(0.25),
        confirmed["max_retracement_sd"].quantile(0.25),
        confirmed["retracement_before_extreme_sd"].quantile(0.25),
        confirmed["retracement_after_05_sd"].quantile(0.25),
    ],
    "P75": [
        confirmed["extension_sd"].quantile(0.75),
        confirmed["max_retracement_sd"].quantile(0.75),
        confirmed["retracement_before_extreme_sd"].quantile(0.75),
        confirmed["retracement_after_05_sd"].quantile(0.75),
    ],
    "P90": [
        confirmed["extension_sd"].quantile(0.90),
        confirmed["max_retracement_sd"].quantile(0.90),
        confirmed["retracement_before_extreme_sd"].quantile(0.90),
        confirmed["retracement_after_05_sd"].quantile(0.90),
    ],
}

pct_df = pd.DataFrame(stats_dict)
pct_df.to_csv(DISTRIBUTIONS_DIR / "extension_percentiles_2024.csv", index=False)

# 2. Breakdown by Range Type (ADR, ODR, RDR)
range_summary = confirmed.groupby("range_type").agg(
    total_events=("confirmed", "count"),
    dr_rule_true_pct=("dr_rule_true", lambda x: (x == True).mean() * 100),
    retraced_into_dr_pct=("retraced_into_dr", lambda x: (x == True).mean() * 100),
    outside_dr_pct=("outside_dr_closed", lambda x: (x == True).mean() * 100),
    median_ext_sd=("extension_sd", "median"),
    median_max_ret_sd=("max_retracement_sd", "median"),
    median_ret_before_extreme_sd=("retracement_before_extreme_sd", "median"),
    median_ret_after_05_sd=("retracement_after_05_sd", "median"),
).reset_index().round(2)
range_summary.to_csv(DISTRIBUTIONS_DIR / "range_summary_2024.csv", index=False)

# 3. Breakdown by Direction (LONG vs SHORT)
dir_summary = confirmed.groupby("direction").agg(
    total_events=("confirmed", "count"),
    dr_rule_true_pct=("dr_rule_true", lambda x: (x == True).mean() * 100),
    retraced_into_dr_pct=("retraced_into_dr", lambda x: (x == True).mean() * 100),
    outside_dr_pct=("outside_dr_closed", lambda x: (x == True).mean() * 100),
    median_ext_sd=("extension_sd", "median"),
    median_max_ret_sd=("max_retracement_sd", "median"),
).reset_index().round(2)
dir_summary.to_csv(DISTRIBUTIONS_DIR / "direction_summary_2024.csv", index=False)

print("Distributions calculated and saved successfully.")