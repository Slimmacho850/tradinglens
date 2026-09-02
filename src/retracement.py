import pandas as pd

# ============================================================
# SETTINGS
# ============================================================

FILE_PATH = "data/DAT_ASCII_NSXUSD_M1_2024.csv"
TEST_DATE = pd.Timestamp("2024-01-02").date()

# ============================================================
# SESSION DEFINITIONS
# ============================================================

SESSIONS = {
    "ADR": {
        "range_start": "19:30",
        "range_end": "20:30",
        "lines_start": "20:30",
        "lines_end": "02:00"
    },
    "ODR": {
        "range_start": "03:00",
        "range_end": "04:00",
        "lines_start": "04:00",
        "lines_end": "08:30"
    },
    "RDR": {
        "range_start": "09:30",
        "range_end": "10:30",
        "lines_start": "10:30",
        "lines_end": "16:00"
    }
}

# ============================================================
# LOAD M1 → M5
# ============================================================

print("Loading M1 data...")

columns = ["datetime", "open", "high", "low", "close", "volume"]
m1 = pd.read_csv(FILE_PATH, sep=";", header=None, names=columns)
m1["datetime"] = pd.to_datetime(m1["datetime"], format="%Y%m%d %H%M%S")
for column in ["open", "high", "low", "close", "volume"]:
    m1[column] = pd.to_numeric(m1[column], errors="coerce")
m1 = m1.dropna().sort_values("datetime").set_index("datetime")

m5 = m1.resample("5min").agg({
    "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
}).dropna()
m5["body_high"] = m5[["open", "close"]].max(axis=1)
m5["body_low"] = m5[["open", "close"]].min(axis=1)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_range_data(trading_date, range_type):
    settings = SESSIONS[range_type]
    if range_type == "ADR":
        actual_date = (pd.Timestamp(trading_date) - pd.Timedelta(days=1)).date()
    else:
        actual_date = trading_date
    start = pd.Timestamp(f"{actual_date} {settings['range_start']}")
    end = pd.Timestamp(f"{actual_date} {settings['range_end']}")
    return m5.loc[(m5.index >= start) & (m5.index < end)]

def get_lines_data(trading_date, range_type):
    settings = SESSIONS[range_type]
    if range_type == "ADR":
        previous_date = (pd.Timestamp(trading_date) - pd.Timedelta(days=1)).date()
        start = pd.Timestamp(f"{previous_date} {settings['lines_start']}")
        end = pd.Timestamp(f"{trading_date} {settings['lines_end']}")
    else:
        start = pd.Timestamp(f"{trading_date} {settings['lines_start']}")
        end = pd.Timestamp(f"{trading_date} {settings['lines_end']}")
    return m5.loc[(m5.index >= start) & (m5.index < end)]

def calculate_range(range_data):
    if len(range_data) != 12:
        return None
    dr_high = range_data["body_high"].max()
    dr_low = range_data["body_low"].min()
    dr_range = dr_high - dr_low
    idr_high = range_data["high"].max()
    idr_low = range_data["low"].min()
    idr_range = idr_high - idr_low
    return {
        "dr_high": dr_high, "dr_low": dr_low, "dr_range": dr_range,
        "idr_high": idr_high, "idr_low": idr_low, "idr_range": idr_range
    }

def find_confirmation(lines_data, idr_high, idr_low):
    for timestamp, candle in lines_data.iterrows():
        close = candle["close"]
        if close > idr_high:
            return {"confirmed": True, "direction": "LONG", "time": timestamp, "price": close}
        if close < idr_low:
            return {"confirmed": True, "direction": "SHORT", "time": timestamp, "price": close}
    return {"confirmed": False, "direction": None, "time": None, "price": None}

def get_m1_lines_data(trading_date, range_type):
    settings = SESSIONS[range_type]
    if range_type == "ADR":
        previous_date = (pd.Timestamp(trading_date) - pd.Timedelta(days=1)).date()
        start = pd.Timestamp(f"{previous_date} {settings['lines_start']}")
        end = pd.Timestamp(f"{trading_date} {settings['lines_end']}")
    else:
        start = pd.Timestamp(f"{trading_date} {settings['lines_start']}")
        end = pd.Timestamp(f"{trading_date} {settings['lines_end']}")
    return m1.loc[(m1.index >= start) & (m1.index < end)]

# ============================================================
# ANALYZE EVENT (first retracement detection)
# ============================================================

def analyze_event(m1_data, confirmation, dr_high, dr_low, dr_range):
    result = {
        "extension_started": False,
        "extension_price": None,
        "extension_time": None,
        "extension_sd": None,
        "retracement_occurred": False,
        "retracement_price": None,
        "retracement_time": None,
        "retracement_exact": None,
        "retracement_grade": None,
        "reached_05_sd": False,
        "time_05_sd": None
    }

    if not confirmation["confirmed"] or dr_range <= 0:
        return result

    start_time = confirmation["time"] + pd.Timedelta(minutes=5)
    end_time = pd.Timestamp(f"{confirmation['time'].date()} 18:00:00")
    data = m1_data.loc[(m1_data.index >= start_time) & (m1_data.index < end_time)]
    if data.empty:
        return result

    direction = confirmation["direction"]

    # ========== SHORT ==========
    if direction == "SHORT":
        extension_started = False
        lowest_price = None
        lowest_time = None
        reached_05 = False
        time_05 = None

        for timestamp, candle in data.iterrows():
            candle_high = candle["high"]
            candle_low = candle["low"]

            if not extension_started:
                if candle_low < dr_low:
                    extension_started = True
                    lowest_price = candle_low
                    lowest_time = timestamp
                    result["extension_started"] = True
                continue

            if candle_low < lowest_price:
                lowest_price = candle_low
                lowest_time = timestamp

            current_sd = max(0.0, dr_low - lowest_price) / dr_range
            if not reached_05 and current_sd >= 0.5:
                reached_05 = True
                time_05 = timestamp

            if candle_high >= dr_low:
                retracement_price = min(candle_high, dr_high)
                retracement_exact = (retracement_price - dr_low) / dr_range
                retracement_exact = max(0.0, min(1.0, retracement_exact))
                result.update({
                    "extension_started": True,
                    "extension_price": lowest_price,
                    "extension_time": lowest_time,
                    "extension_sd": (dr_low - lowest_price) / dr_range,
                    "retracement_occurred": True,
                    "retracement_price": retracement_price,
                    "retracement_time": timestamp,
                    "retracement_exact": retracement_exact,
                    "retracement_grade": int(retracement_exact * 10) / 10,
                    "reached_05_sd": reached_05,
                    "time_05_sd": time_05
                })
                return result

        if extension_started:
            result.update({
                "extension_price": lowest_price,
                "extension_time": lowest_time,
                "extension_sd": (dr_low - lowest_price) / dr_range,
                "reached_05_sd": reached_05,
                "time_05_sd": time_05
            })
        return result

    # ========== LONG ==========
    extension_started = False
    highest_price = None
    highest_time = None
    reached_05 = False
    time_05 = None

    for timestamp, candle in data.iterrows():
        candle_high = candle["high"]
        candle_low = candle["low"]
        breaks_dr = candle_high > dr_high   # <-- FIXED: defined here
        returns_to_dr = candle_low <= dr_high

        if not extension_started:
            if breaks_dr:
                extension_started = True
                highest_price = candle_high
                highest_time = timestamp
                result["extension_started"] = True
            continue

        if candle_high > highest_price:
            highest_price = candle_high
            highest_time = timestamp

        current_sd = max(0.0, highest_price - dr_high) / dr_range
        if not reached_05 and current_sd >= 0.5:
            reached_05 = True
            time_05 = timestamp

        if returns_to_dr:
            retracement_price = max(candle_low, dr_low)
            retracement_exact = (dr_high - retracement_price) / dr_range
            retracement_exact = max(0.0, min(1.0, retracement_exact))
            result.update({
                "extension_started": True,
                "extension_price": highest_price,
                "extension_time": highest_time,
                "extension_sd": (highest_price - dr_high) / dr_range,
                "retracement_occurred": True,
                "retracement_price": retracement_price,
                "retracement_time": timestamp,
                "retracement_exact": retracement_exact,
                "retracement_grade": int(retracement_exact * 10) / 10,
                "reached_05_sd": reached_05,
                "time_05_sd": time_05
            })
            return result

    if extension_started:
        result.update({
            "extension_price": highest_price,
            "extension_time": highest_time,
            "extension_sd": (highest_price - dr_high) / dr_range,
            "reached_05_sd": reached_05,
            "time_05_sd": time_05
        })
    return result

# ============================================================
# TEST FOR THE GIVEN DATE
# ============================================================

print("\n======================================")
print("FIRST RETRACEMENT TEST")
print("======================================")
print("Trading Date:", TEST_DATE)

results = []

for range_type in SESSIONS:
    print("\n--------------------------------------")
    print(range_type)
    print("--------------------------------------")

    range_data = get_range_data(TEST_DATE, range_type)
    print("Range candles:", len(range_data))
    if len(range_data) != 12:
        print("INVALID RANGE")
        continue

    range_values = calculate_range(range_data)
    lines_data = get_lines_data(TEST_DATE, range_type)
    confirmation = find_confirmation(lines_data, range_values["idr_high"], range_values["idr_low"])

    print("Confirmed:", confirmation["confirmed"])
    print("Direction:", confirmation["direction"])
    print("Confirmation:", confirmation["time"])

    m1_lines = get_m1_lines_data(TEST_DATE, range_type)
    event = analyze_event(m1_lines, confirmation, range_values["dr_high"], range_values["dr_low"], range_values["dr_range"])

    results.append({
        "trading_date": TEST_DATE,
        "range_type": range_type,
        "direction": confirmation["direction"],
        "confirmation_time": confirmation["time"],
        "confirmation_price": confirmation["price"],
        "dr_high": range_values["dr_high"],
        "dr_low": range_values["dr_low"],
        "dr_range": range_values["dr_range"],
        "extension_started": event["extension_started"],
        "extension_price": event["extension_price"],
        "extension_time": event["extension_time"],
        "extension_sd": event["extension_sd"],
        "retracement_occurred": event["retracement_occurred"],
        "retracement_price": event["retracement_price"],
        "retracement_time": event["retracement_time"],
        "retracement_exact": event["retracement_exact"],
        "retracement_grade": event["retracement_grade"],
        "reached_05_sd": event["reached_05_sd"],
        "time_05_sd": event["time_05_sd"]
    })

result = pd.DataFrame(results)
print("\n======================================")
print("RESULT")
print("======================================")
print(result.to_string(index=False))