import sys
from pathlib import Path
import pandas as pd

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ============================================================
# DR LENS HOD / LOD SUMMARY
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
DATABASE_DIR = ROOT / "database"
DISTRIBUTIONS_DIR = DATABASE_DIR / "distributions"
INPUT_FILE = DATABASE_DIR / "events_master.csv" if (DATABASE_DIR / "events_master.csv").exists() else (DATABASE_DIR / "events_2024.csv")

DISTRIBUTIONS_DIR.mkdir(parents=True, exist_ok=True)

print(f"Running HOD / LOD distribution generator from {INPUT_FILE.name}...")
df = pd.read_csv(INPUT_FILE)
confirmed = df[df["confirmed"] == True].copy()

# Summary table for HOD/LOD metrics
summary = confirmed.groupby(["range_type", "direction"]).agg(
    total_events=("confirmed", "count"),
    median_ext_sd=("extension_sd", "median"),
    median_ret_before_extreme=("retracement_before_extreme_sd", "median"),
    median_max_ret=("max_retracement_sd", "median"),
    dr_rule_true_pct=("dr_rule_true", lambda x: (x == True).mean() * 100),
    retraced_into_dr_pct=("retraced_into_dr", lambda x: (x == True).mean() * 100),
).reset_index().round(2)

output_file = DISTRIBUTIONS_DIR / "hod_lod_range_summary_2024.csv"
summary.to_csv(output_file, index=False)

print(f"HOD/LOD summary generated successfully. Saved to {output_file}")