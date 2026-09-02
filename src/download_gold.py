"""
Gold (XAU/USD) Historical Data Downloader for Trading Lens (2025 - Present)
Downloads 1-Minute Candlestick data directly from Dukascopy datafeed and formats
as ASCII M1 files in America/New_York (US Eastern Time).

Output Files:
- data/DAT_ASCII_XAUUSD_M1_2025.csv
- data/DAT_ASCII_XAUUSD_M1_2026.csv
Format: YYYYMMDD HHMMSS;open;high;low;close;volume
"""

import sys
import os
import lzma
import struct
import time
from pathlib import Path
from datetime import datetime, timezone
import zoneinfo
import concurrent.futures
import threading
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

NY_TZ = zoneinfo.ZoneInfo("America/New_York")
UTC_TZ = timezone.utc

SYMBOL = "XAUUSD"
SYMBOL_PREFIX = "DAT_ASCII_XAUUSD_M1"
POINT_DIVIDER = 1000.0  # Dukascopy gold prices are integer * 1000

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

_thread_local = threading.local()

def get_session():
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=5, max_retries=2)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        _thread_local.session = s
    return _thread_local.session


def fetch_day_candles(year: int, month_0indexed: int, day: int) -> list[tuple[int, str]]:
    """
    Fetches M1 candle bi5 file from Dukascopy for a specific UTC date.
    Dukascopy month is 0-indexed: 00 = Jan, 11 = Dec.
    Returns a list of tuples: (timestamp_ms, formatted_ascii_row).
    """
    url = f"http://datafeed.dukascopy.com/datafeed/{SYMBOL}/{year:04d}/{month_0indexed:02d}/{day:02d}/BID_candles_min_1.bi5"
    
    day_start_utc = datetime(year, month_0indexed + 1, day, 0, 0, 0, tzinfo=UTC_TZ)
    day_start_ts = int(day_start_utc.timestamp())
    session = get_session()
    
    retries = 3
    while retries > 0:
        try:
            resp = session.get(url, headers=HEADERS, timeout=8)
            if resp.status_code == 404:
                return []
            if resp.status_code != 200 or len(resp.content) == 0:
                return []
            
            dec = lzma.decompress(resp.content)
            record_size = 24
            num_records = len(dec) // record_size
            candles = []
            
            for i in range(num_records):
                chunk = dec[i * record_size : (i + 1) * record_size]
                sec_offset, o_raw, c_raw, l_raw, h_raw, vol = struct.unpack(">iiiiif", chunk)
                
                # Skip invalid / flat zero candles
                if o_raw <= 0 or h_raw <= 0 or l_raw <= 0 or c_raw <= 0:
                    continue
                
                o = o_raw / POINT_DIVIDER
                c = c_raw / POINT_DIVIDER
                l = l_raw / POINT_DIVIDER
                h = h_raw / POINT_DIVIDER
                
                candle_utc = datetime.fromtimestamp(day_start_ts + sec_offset, tz=UTC_TZ)
                candle_ny = candle_utc.astimezone(NY_TZ)
                
                ny_str = candle_ny.strftime("%Y%m%d %H%M%S")
                row_str = f"{ny_str};{o:.6f};{h:.6f};{l:.6f};{c:.6f};0\n"
                
                candles.append((day_start_ts + sec_offset, row_str))
            
            return candles
        except Exception:
            retries -= 1
            if retries > 0:
                time.sleep(0.3)
            else:
                return []
    return []


def download_year_gold_data(year: int):
    now = datetime.now(UTC_TZ)
    current_year = now.year
    current_month = now.month - 1  # 0-indexed
    current_day = now.day
    
    target_file = DATA_DIR / f"{SYMBOL_PREFIX}_{year}.csv"
    print(f"\n======================================================", flush=True)
    print(f"📥 Downloading Gold (XAU/USD) for Year {year}...", flush=True)
    print(f"Target: {target_file}", flush=True)
    print(f"======================================================", flush=True)
    
    start_time = time.time()
    all_candles = []
    
    max_month = current_month if year == current_year else 11
    
    days_to_fetch = []
    for m in range(max_month + 1):
        if m in [0, 2, 4, 6, 7, 9, 11]:
            days_in_month = 31
        elif m in [3, 5, 8, 10]:
            days_in_month = 30
        else:
            is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
            days_in_month = 29 if is_leap else 28
        
        max_d = current_day if (year == current_year and m == current_month) else days_in_month
        for d in range(1, max_d + 1):
            days_to_fetch.append((year, m, d))
            
    print(f"  ⏳ Fetching {len(days_to_fetch)} calendar days with 20 worker threads...", flush=True)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_day = {
            executor.submit(fetch_day_candles, y, m, d): (y, m, d)
            for (y, m, d) in days_to_fetch
        }
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_day):
            completed += 1
            try:
                res = future.result()
                if res:
                    all_candles.extend(res)
            except Exception:
                pass
            if completed % 50 == 0 or completed == len(days_to_fetch):
                print(f"    Progress: {completed}/{len(days_to_fetch)} days fetched ({len(all_candles):,} candles so far)...", flush=True)
    
    if not all_candles:
        print(f"⚠️ No candle data retrieved for Gold {year}", flush=True)
        return
    
    all_candles.sort(key=lambda x: x[0])
    
    seen = set()
    unique_rows = []
    for ts, row in all_candles:
        if ts not in seen:
            seen.add(ts)
            unique_rows.append(row)
            
    print(f"  ✓ Processed {len(unique_rows):,} unique 1-minute Gold candles", flush=True)
    print(f"  💾 Writing to {target_file}...", flush=True)
    
    with open(target_file, "w", encoding="utf-8") as f:
        f.writelines(unique_rows)
        
    elapsed = time.time() - start_time
    file_size_mb = os.path.getsize(target_file) / (1024 * 1024)
    print(f"  🎉 Finished {target_file.name} ({file_size_mb:.2f} MB) in {elapsed:.1f}s", flush=True)


def main():
    print("🚀 STARTING GOLD (XAU/USD) HISTORICAL DATA DOWNLOAD", flush=True)
    now_year = datetime.now(UTC_TZ).year
    years = [2025, now_year] if now_year >= 2025 else [2025]
    for y in sorted(set(years)):
        download_year_gold_data(y)
    print("\n🎉 ALL GOLD HISTORICAL DATA DOWNLOADS COMPLETED SUCCESSFULLY!", flush=True)


if __name__ == "__main__":
    main()
