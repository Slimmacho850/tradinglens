"""
Weekly Database Ingestion & Updater Pipeline for Trading Lens
Automatically downloads the past week's 1-minute data for all instruments,
merges into raw M1 archives, computes Defining Ranges (ADR, ODR, RDR),
unclipped retracements, and updates the master database and distribution tables.
"""

import datetime
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import zoneinfo

# Ensure src directory is in sys.path
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

# Import core dataset processor from historical_events_2024
from historical_events_2024 import (
    process_dataset,
    DATABASE_DIR,
    DISTRIBUTIONS_DIR,
    DATA_DIR,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
EVENTS_MASTER_FILE = DATABASE_DIR / "events_master.csv"

NY_TZ = zoneinfo.ZoneInfo("America/New_York")

# Instrument Mapping for Yahoo Finance -> ASCII Files
INSTRUMENT_CONFIGS = [
    {
        "symbol": "NQ",
        "name": "E-mini Nasdaq 100",
        "ticker": "NQ=F",
        "prefix": "DAT_ASCII_NSXUSD_M1",
        "price_format": "%.2f",
    },
    {
        "symbol": "ES",
        "name": "E-mini S&P 500",
        "ticker": "ES=F",
        "prefix": "DAT_ASCII_SPXUSD_M1",
        "price_format": "%.2f",
    },
    {
        "symbol": "GC",
        "name": "Gold Futures",
        "ticker": "GC=F",
        "prefix": "DAT_ASCII_XAUUSD_M1",
        "price_format": "%.2f",
    },
    {
        "symbol": "YM",
        "name": "E-mini Dow Jones",
        "ticker": "YM=F",
        "prefix": "DAT_ASCII_YM_M1",
        "price_format": "%.2f",
    },
    {
        "symbol": "6E",
        "name": "Euro FX Spot",
        "ticker": "EURUSD=X",
        "prefix": "DAT_ASCII_EURUSD_M1",
        "price_format": "%.6f",
    },
]


def fetch_symbol_m1(ticker: str, days: int = 7) -> pd.DataFrame:
    """
    Downloads 1-minute candlestick data from Yahoo Finance in America/New_York timezone.
    """
    if yf is None:
        print(f"  ⚠️ 'yfinance' is not installed in the environment. Skipping live download for {ticker}.", flush=True)
        return pd.DataFrame()

    try:
        df = yf.download(ticker, period=f"{days}d", interval="1m", progress=False)
        if df.empty:
            return pd.DataFrame()

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.columns = [c.strip().lower() for c in df.columns]

        # Convert index to NY Timezone
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(NY_TZ)
        else:
            df.index = df.index.tz_convert(NY_TZ)

        df.index = df.index.tz_localize(None)  # Remove tz for clean comparison

        df = df[["open", "high", "low", "close"]].dropna()
        df = df.sort_index().drop_duplicates()
        return df
    except Exception as e:
        print(f"  ⚠️ Error fetching {ticker}: {e}", flush=True)
        return pd.DataFrame()


def merge_m1_into_archive(df_new: pd.DataFrame, prefix: str, year: int) -> Path:
    """
    Appends and merges new 1-minute data into the corresponding annual ASCII archive file.
    Format: YYYYMMDD HHMMSS;open;high;low;close;volume
    """
    target_file = DATA_DIR / f"{prefix}_{year}.csv"
    existing_records: Dict[str, Tuple[float, float, float, float]] = {}

    if target_file.exists():
        with open(target_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str or ";" not in line_str:
                    continue
                parts = line_str.split(";")
                if len(parts) >= 5:
                    dt_str = parts[0]
                    try:
                        o, h, l, c = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                        existing_records[dt_str] = (o, h, l, c)
                    except ValueError:
                        continue

    # Insert / update new records
    for dt, row in df_new.iterrows():
        if dt.year != year:
            continue
        dt_str = dt.strftime("%Y%m%d %H%M%S")
        existing_records[dt_str] = (float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]))

    # Sort chronologically and rewrite
    sorted_keys = sorted(existing_records.keys())
    lines = [f"{k};{existing_records[k][0]:.6f};{existing_records[k][1]:.6f};{existing_records[k][2]:.6f};{existing_records[k][3]:.6f};0\n" for k in sorted_keys]

    with open(target_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"  ✓ Updated {target_file.name}: {len(sorted_keys):,} total 1m candles", flush=True)
    return target_file


def run_weekly_update(days_back: int = 7) -> Dict[str, any]:
    """
    Executes the full weekly ingestion, session computation, and database update pipeline.
    """
    print("=" * 65, flush=True)
    print(f"🚀 STARTING TRADING LENS WEEKLY DATABASE SYNC ({days_back} DAYS)", flush=True)
    print("=" * 65, flush=True)

    current_year = datetime.datetime.now().year
    updated_files: List[Path] = []
    symbol_summaries = {}

    # 1. Download and merge 1m data for each instrument
    for config in INSTRUMENT_CONFIGS:
        sym = config["symbol"]
        ticker = config["ticker"]
        prefix = config["prefix"]
        name = config["name"]

        print(f"\n📡 Ingesting {name} ({ticker})...", flush=True)
        df_1m = fetch_symbol_m1(ticker, days=days_back)

        if df_1m.empty:
            print(f"  ⚠️ No recent 1m data returned for {sym}", flush=True)
            symbol_summaries[sym] = 0
            continue

        print(f"  ✓ Fetched {len(df_1m):,} live 1m candles ({df_1m.index.min():%Y-%m-%d} to {df_1m.index.max():%Y-%m-%d})", flush=True)

        target_file = merge_m1_into_archive(df_1m, prefix, current_year)
        updated_files.append(target_file)

    if not updated_files:
        print("\n⚠️ No new data files were updated.", flush=True)
        return {"status": "no_data", "total_added": 0, "breakdown": symbol_summaries}

    # 2. Process all updated annual files through the DR engine
    print(f"\n⚡ Processing Defining Range sessions for updated files...", flush=True)
    new_frames = []
    for f in updated_files:
        df_events = process_dataset(f)
        if not df_events.empty:
            new_frames.append(df_events)
            inst = df_events["instrument"].iloc[0] if "instrument" in df_events.columns else f.name
            symbol_summaries[inst] = len(df_events)

    if not new_frames:
        print("\n⚠️ No session events generated.", flush=True)
        return {"status": "no_events", "total_added": 0, "breakdown": symbol_summaries}

    new_combined_df = pd.concat(new_frames, ignore_index=True)
    new_combined_df["trading_date"] = pd.to_datetime(new_combined_df["trading_date"])

    # 3. Merge into Master Database with zero duplicate sessions
    if EVENTS_MASTER_FILE.exists():
        master_df = pd.read_csv(EVENTS_MASTER_FILE)
        master_df["trading_date"] = pd.to_datetime(master_df["trading_date"])
        
        # Concat and deduplicate on [instrument, trading_date, range_type] keeping newest
        combined_df = pd.concat([master_df, new_combined_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=["instrument", "trading_date", "range_type"], keep="last")
        combined_df = combined_df.sort_values(["trading_date", "range_type", "instrument"]).reset_index(drop=True)
    else:
        combined_df = new_combined_df.sort_values(["trading_date", "range_type", "instrument"]).reset_index(drop=True)

    combined_df.to_csv(EVENTS_MASTER_FILE, index=False)
    print(f"\n💾 Saved Master Database: {len(combined_df):,} total sessions ({EVENTS_MASTER_FILE})", flush=True)

    # 4. Also update yearly and instrument-specific event files
    for y in combined_df["trading_date"].dt.year.unique():
        df_y = combined_df[combined_df["trading_date"].dt.year == int(y)]
        if not df_y.empty:
            df_y.to_csv(DATABASE_DIR / f"events_{y}.csv", index=False)

    for sym in combined_df["instrument"].unique():
        sym_df = combined_df[combined_df["instrument"] == sym]
        sym_file = DATABASE_DIR / f"events_{sym.lower()}.csv"
        sym_df.to_csv(sym_file, index=False)

    # 5. Update distribution files
    confirmed_df = combined_df[combined_df["confirmed"] == True].copy()
    confirmed_df.to_csv(DISTRIBUTIONS_DIR / "maximum_retracement_before_hod_lod.csv", index=False)

    print("=" * 65, flush=True)
    print(f"🎉 WEEKLY DATABASE SYNC COMPLETED SUCCESSFULLY!")
    print(f"Total Master Sessions: {len(combined_df):,}")
    print(f"Confirmed Events: {len(confirmed_df):,}")
    print(f"Date Coverage: {combined_df['trading_date'].min():%Y-%m-%d} to {combined_df['trading_date'].max():%Y-%m-%d}")
    print("=" * 65, flush=True)

    return {
        "status": "success",
        "total_sessions": len(combined_df),
        "confirmed_events": len(confirmed_df),
        "min_date": str(combined_df['trading_date'].min().date()),
        "max_date": str(combined_df['trading_date'].max().date()),
        "breakdown": symbol_summaries,
    }


if __name__ == "__main__":
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass
    run_weekly_update(days_back=days)
