import sys
from pathlib import Path
import glob
import pandas as pd
import numpy as np

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ============================================================
# DR LENS - MULTI-INSTRUMENT MASTER DATABASE BUILDER
# Supports 2010-2026 multi-year & multi-instrument datasets
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATABASE_DIR = ROOT / "database"
DISTRIBUTIONS_DIR = DATABASE_DIR / "distributions"

DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DISTRIBUTIONS_DIR.mkdir(parents=True, exist_ok=True)

# Session configurations in Eastern Time (ET)
SESSIONS = {
    "ADR": {
        "range_start": "19:30",
        "range_end": "20:30",
        "lines_start": "20:30",
        "lines_end": "02:00",
        "prev_day_range": True,
    },
    "ODR": {
        "range_start": "03:00",
        "range_end": "04:00",
        "lines_start": "04:00",
        "lines_end": "08:30",
        "prev_day_range": False,
    },
    "RDR": {
        "range_start": "09:30",
        "range_end": "10:30",
        "lines_start": "10:30",
        "lines_end": "16:00",
        "prev_day_range": False,
    },
}


def infer_instrument(filename: str) -> str:
    upper = Path(filename).stem.upper()
    if any(k in upper for k in ["XAUUSD", "GOLD", "GC", "XAU"]):
        return "GC"
    if any(k in upper for k in ["NSXUSD", "NQ", "MNQ", "NAS100", "US100"]):
        return "NQ"
    if any(k in upper for k in ["SPXUSD", "ES", "MES", "SP500", "US500", "USA500"]):
        return "ES"
    if any(k in upper for k in ["YM", "MYM", "DOW", "US30"]):
        return "YM"
    if any(k in upper for k in ["RTY", "M2K", "US2000"]):
        return "RTY"
    return upper.split("_")[0] if "_" in upper else "NQ"


def load_m1_data(file_path: Path | str) -> pd.DataFrame:
    """Loads and cleans raw M1 ASCII data supporting multiple standard formats."""
    print(f"\n📂 Loading M1 data: {Path(file_path).name}...")
    
    # Try reading first line to check delimiter and header
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        first_line = f.readline()

    sep = ";" if ";" in first_line else "," if "," in first_line else "\t"
    has_header = any(col in first_line.lower() for col in ["date", "time", "open", "close"])

    if has_header:
        df = pd.read_csv(file_path, sep=sep)
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Unify datetime column
        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        elif "date" in df.columns and "time" in df.columns:
            df["datetime"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str), errors="coerce")
        elif "date" in df.columns:
            df["datetime"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        columns = ["datetime", "open", "high", "low", "close", "volume"]
        df = pd.read_csv(file_path, sep=sep, header=None, names=columns)
        df["datetime"] = pd.to_datetime(df["datetime"], format="%Y%m%d %H%M%S", errors="coerce")

    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["datetime", "open", "high", "low", "close"])
    df = df.sort_values("datetime").drop_duplicates("datetime").set_index("datetime")
    print(f"  ✓ Loaded {len(df):,} valid M1 candles ({df.index.min():%Y-%m-%d} to {df.index.max():%Y-%m-%d})")
    return df


def resample_m5(m1: pd.DataFrame) -> pd.DataFrame:
    """Resamples M1 DataFrame to M5 OHLCV with body boundaries."""
    m5 = m1.resample("5min").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum" if "volume" in m1.columns else "count",
    }).dropna()

    m5["body_high"] = m5[["open", "close"]].max(axis=1)
    m5["body_low"] = m5[["open", "close"]].min(axis=1)
    return m5


def process_dataset(m1_file: Path) -> pd.DataFrame:
    instrument = infer_instrument(m1_file.name)
    m1 = load_m1_data(m1_file)
    if m1.empty:
        return pd.DataFrame()

    m5 = resample_m5(m1)

    # Weekday trading dates (Mon-Fri) present in dataset
    weekdays = sorted(set(d for d in m5.index.date if d.weekday() < 5))

    print(f"  ⚡ Processing {len(weekdays):,} trading days for {instrument}...")

    all_events = []

    for trading_date in weekdays:
        t_date_str = str(trading_date)
        prev_date = trading_date - pd.Timedelta(days=1)
        prev_date_str = str(prev_date)
        day_name = pd.Timestamp(trading_date).day_name()

        for range_type, cfg in SESSIONS.items():
            if cfg["prev_day_range"]:
                r_start = pd.Timestamp(f"{prev_date_str} {cfg['range_start']}:00")
                r_end = pd.Timestamp(f"{prev_date_str} {cfg['range_end']}:00")
                l_start = pd.Timestamp(f"{prev_date_str} {cfg['lines_start']}:00")
                l_end = pd.Timestamp(f"{t_date_str} {cfg['lines_end']}:00")
            else:
                r_start = pd.Timestamp(f"{t_date_str} {cfg['range_start']}:00")
                r_end = pd.Timestamp(f"{t_date_str} {cfg['range_end']}:00")
                l_start = pd.Timestamp(f"{t_date_str} {cfg['lines_start']}:00")
                l_end = pd.Timestamp(f"{t_date_str} {cfg['lines_end']}:00")

            range_m5 = m5.loc[(m5.index >= r_start) & (m5.index < r_end)]
            if len(range_m5) != 12:
                continue

            dr_high = float(range_m5["body_high"].max())
            dr_low = float(range_m5["body_low"].min())
            dr_range = float(dr_high - dr_low)

            idr_high = float(range_m5["high"].max())
            idr_low = float(range_m5["low"].min())
            idr_range = float(idr_high - idr_low)

            if dr_range <= 0:
                continue

            lines_m5 = m5.loc[(m5.index >= l_start) & (m5.index < l_end)]
            lines_m1 = m1.loc[(m1.index >= l_start) & (m1.index < l_end)]

            # Confirmation detection
            confirmed = False
            direction = None
            conf_time = None
            conf_price = None

            for ts, candle in lines_m5.iterrows():
                close_p = float(candle["close"])
                if close_p > idr_high:
                    confirmed = True
                    direction = "LONG"
                    conf_time = ts
                    conf_price = close_p
                    break
                elif close_p < idr_low:
                    confirmed = True
                    direction = "SHORT"
                    conf_time = ts
                    conf_price = close_p
                    break

            dr_rule_true = None
            retraced_into_dr = None
            outside_dr_closed = None

            extension_sd = None
            extension_price = None
            extension_time = None

            max_retracement_sd = None
            max_retracement_price = None
            max_retracement_time = None

            reached_05_sd = False
            time_05_sd = None

            retracement_before_extreme_sd = None
            retracement_after_05_sd = None

            first_retracement_occurred = False
            first_retracement_price = None
            first_retracement_time = None
            first_retracement_exact = None

            session_max_high = float(lines_m1["high"].max()) if not lines_m1.empty else dr_high
            session_min_low = float(lines_m1["low"].min()) if not lines_m1.empty else dr_low
            mean_sd_up = max(0.0, (session_max_high - dr_high) / dr_range)
            mean_sd_down = max(0.0, (dr_low - session_min_low) / dr_range)

            if confirmed and conf_time is not None:
                post_conf_m5_lines = lines_m5.loc[lines_m5.index >= conf_time]
                
                # DR Rule True/False
                if direction == "LONG":
                    dr_rule_true = not (post_conf_m5_lines["close"] < dr_low).any()
                elif direction == "SHORT":
                    dr_rule_true = not (post_conf_m5_lines["close"] > dr_high).any()

                post_conf_m1 = lines_m1.loc[lines_m1.index >= conf_time + pd.Timedelta(minutes=5)]

                if not post_conf_m1.empty:
                    if direction == "LONG":
                        extreme_val = float(post_conf_m1["high"].max())
                        ext_idx = post_conf_m1["high"].idxmax()
                        extension_price = extreme_val
                        extension_time = ext_idx
                        extension_sd = max(0.0, (extreme_val - dr_high) / dr_range)

                        ret_candles = post_conf_m1[post_conf_m1["low"] <= dr_high]
                        if not ret_candles.empty:
                            retraced_into_dr = True
                            first_ret_row = ret_candles.iloc[0]
                            first_retracement_occurred = True
                            first_retracement_price = float(first_ret_row["low"])
                            first_retracement_time = first_ret_row.name
                            first_retracement_exact = max(0.0, min(1.0, (dr_high - first_retracement_price) / dr_range))
                        else:
                            retraced_into_dr = False

                        lowest_p = float(post_conf_m1["low"].min())
                        lowest_ts = post_conf_m1["low"].idxmin()
                        max_retracement_price = lowest_p
                        max_retracement_time = lowest_ts
                        max_retracement_sd = max(0.0, (dr_high - lowest_p) / dr_range)

                        pre_extreme_m1 = post_conf_m1.loc[post_conf_m1.index <= extension_time]
                        if not pre_extreme_m1.empty:
                            pre_lowest = float(pre_extreme_m1["low"].min())
                            retracement_before_extreme_sd = max(0.0, (dr_high - pre_lowest) / dr_range)
                        else:
                            retracement_before_extreme_sd = 0.0

                        candles_05 = post_conf_m1[post_conf_m1["high"] >= dr_high + 0.5 * dr_range]
                        if not candles_05.empty:
                            reached_05_sd = True
                            time_05_sd = candles_05.iloc[0].name
                            post_05_m1 = post_conf_m1.loc[post_conf_m1.index >= time_05_sd]
                            if not post_05_m1.empty:
                                post_05_lowest = float(post_05_m1["low"].min())
                                retracement_after_05_sd = max(0.0, (dr_high - post_05_lowest) / dr_range)

                        if retraced_into_dr and not lines_m5.empty:
                            final_close = float(lines_m5.iloc[-1]["close"])
                            outside_dr_closed = bool(final_close > dr_high)

                    elif direction == "SHORT":
                        extreme_val = float(post_conf_m1["low"].min())
                        ext_idx = post_conf_m1["low"].idxmin()
                        extension_price = extreme_val
                        extension_time = ext_idx
                        extension_sd = max(0.0, (dr_low - extreme_val) / dr_range)

                        ret_candles = post_conf_m1[post_conf_m1["high"] >= dr_low]
                        if not ret_candles.empty:
                            retraced_into_dr = True
                            first_ret_row = ret_candles.iloc[0]
                            first_retracement_occurred = True
                            first_retracement_price = float(first_ret_row["high"])
                            first_retracement_time = first_ret_row.name
                            first_retracement_exact = max(0.0, min(1.0, (first_retracement_price - dr_low) / dr_range))
                        else:
                            retraced_into_dr = False

                        highest_p = float(post_conf_m1["high"].max())
                        highest_ts = post_conf_m1["high"].idxmax()
                        max_retracement_price = highest_p
                        max_retracement_time = highest_ts
                        max_retracement_sd = max(0.0, (highest_p - dr_low) / dr_range)

                        pre_extreme_m1 = post_conf_m1.loc[post_conf_m1.index <= extension_time]
                        if not pre_extreme_m1.empty:
                            pre_highest = float(pre_extreme_m1["high"].max())
                            retracement_before_extreme_sd = max(0.0, (pre_highest - dr_low) / dr_range)
                        else:
                            retracement_before_extreme_sd = 0.0

                        candles_05 = post_conf_m1[post_conf_m1["low"] <= dr_low - 0.5 * dr_range]
                        if not candles_05.empty:
                            reached_05_sd = True
                            time_05_sd = candles_05.iloc[0].name
                            post_05_m1 = post_conf_m1.loc[post_conf_m1.index >= time_05_sd]
                            if not post_05_m1.empty:
                                post_05_highest = float(post_05_m1["high"].max())
                                retracement_after_05_sd = max(0.0, (post_05_highest - dr_low) / dr_range)

                        if retraced_into_dr and not lines_m5.empty:
                            final_close = float(lines_m5.iloc[-1]["close"])
                            outside_dr_closed = bool(final_close < dr_low)

            event_record = {
                "instrument": instrument,
                "trading_date": t_date_str,
                "day_of_week": day_name,
                "range_type": range_type,
                "dr_high": dr_high,
                "dr_low": dr_low,
                "dr_range": dr_range,
                "idr_high": idr_high,
                "idr_low": idr_low,
                "idr_range": idr_range,
                "confirmed": confirmed,
                "direction": direction,
                "confirmation_time": str(conf_time) if conf_time is not None else None,
                "confirmation_price": conf_price,
                "dr_rule_true": dr_rule_true,
                "retraced_into_dr": retraced_into_dr,
                "outside_dr_closed": outside_dr_closed,
                "mean_sd_up": round(mean_sd_up, 4),
                "mean_sd_down": round(mean_sd_down, 4),
                "extension_sd": round(extension_sd, 4) if extension_sd is not None else None,
                "extension_price": extension_price,
                "extension_time": str(extension_time) if extension_time is not None else None,
                "max_retracement_sd": round(max_retracement_sd, 4) if max_retracement_sd is not None else None,
                "max_retracement_price": max_retracement_price,
                "max_retracement_time": str(max_retracement_time) if max_retracement_time is not None else None,
                "reached_05_sd": reached_05_sd,
                "time_05_sd": str(time_05_sd) if time_05_sd is not None else None,
                "retracement_before_extreme_sd": round(retracement_before_extreme_sd, 4) if retracement_before_extreme_sd is not None else None,
                "retracement_after_05_sd": round(retracement_after_05_sd, 4) if retracement_after_05_sd is not None else None,
                "first_retracement_occurred": first_retracement_occurred,
                "first_retracement_price": first_retracement_price,
                "first_retracement_time": str(first_retracement_time) if first_retracement_time is not None else None,
                "first_retracement_exact": round(first_retracement_exact, 4) if first_retracement_exact is not None else None,
            }

            all_events.append(event_record)

    events_df = pd.DataFrame(all_events)
    return events_df


def build_all_databases():
    """Finds all CSV files in data/ and combines them into master databases."""
    raw_files = list(DATA_DIR.glob("*.csv"))
    if not raw_files:
        print(f"No CSV files found in {DATA_DIR}")
        return

    frames = []
    for f in raw_files:
        df_inst = process_dataset(f)
        if not df_inst.empty:
            frames.append(df_inst)

    if not frames:
        print("No events were generated.")
        return

    master_df = pd.concat(frames, ignore_index=True)
    master_df = master_df.drop_duplicates(subset=["instrument", "trading_date", "range_type"]).sort_values(["instrument", "trading_date", "range_type"]).reset_index(drop=True)

    # Save unified master events file
    master_file = DATABASE_DIR / "events_master.csv"
    master_df.to_csv(master_file, index=False)

    # Also keep events_2024.csv / historical_2024.csv and all yearly files updated
    for y in master_df["trading_date"].apply(lambda d: str(d)[:4]).unique():
        df_y = master_df[pd.to_datetime(master_df["trading_date"]).dt.year == int(y)]
        if not df_y.empty:
            df_y.to_csv(DATABASE_DIR / f"events_{y}.csv", index=False)
            if int(y) == 2024:
                df_y.to_csv(DATABASE_DIR / "historical_2024.csv", index=False)

    # Generate distribution files
    confirmed_df = master_df[master_df["confirmed"] == True].copy()
    confirmed_df.to_csv(DISTRIBUTIONS_DIR / "maximum_retracement_before_hod_lod.csv", index=False)

    print(f"\n=======================================================")
    print(f"🎉 MASTER DATABASE BUILT SUCCESSFULLY!")
    print(f"Total Sessions: {len(master_df):,}")
    print(f"Confirmed Events: {len(confirmed_df):,}")
    print(f"Instruments: {', '.join(master_df['instrument'].unique())}")
    print(f"Date Range: {master_df['trading_date'].min()} to {master_df['trading_date'].max()}")
    print(f"Saved: {master_file}")
    print(f"=======================================================\n")


if __name__ == "__main__":
    build_all_databases()