import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

FILE_PATH = "data/DAT_ASCII_NSXUSD_M1_2024.csv"


# ============================================================
# LOAD M1 DATA
# ============================================================

columns = [
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume"
]

m1 = pd.read_csv(
    FILE_PATH,
    sep=";",
    header=None,
    names=columns
)

m1["datetime"] = pd.to_datetime(
    m1["datetime"],
    format="%Y%m%d %H%M%S"
)

for column in ["open", "high", "low", "close", "volume"]:
    m1[column] = pd.to_numeric(
        m1[column],
        errors="coerce"
    )

m1 = m1.dropna()
m1 = m1.sort_values("datetime")


# ============================================================
# M1 → M5
# ============================================================

m1 = m1.set_index("datetime")

m5 = m1.resample("5min").agg({
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"
})

m5 = m5.dropna()


# ============================================================
# DR BODY VALUES
# ============================================================

m5["body_high"] = m5[["open", "close"]].max(axis=1)
m5["body_low"] = m5[["open", "close"]].min(axis=1)


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
# GET SESSION DATA
# ============================================================

def get_session_data(trading_date, start_time, end_time):

    start = pd.Timestamp(
        f"{trading_date} {start_time}"
    )

    end = pd.Timestamp(
        f"{trading_date} {end_time}"
    )

    # If end is earlier than start, it crosses midnight
    if end <= start:
        end += pd.Timedelta(days=1)

    return m5.loc[
        (m5.index >= start) &
        (m5.index < end)
    ]


# ============================================================
# CALCULATE RANGE
# ============================================================

def calculate_range(trading_date, start_time, end_time):

    # --------------------------------------------------------
    # ADR belongs to the evening BEFORE the trading date.
    #
    # Example:
    #
    # Trading date = 2024-01-02
    #
    # ADR = Jan 1 19:30 → Jan 1 20:30
    # --------------------------------------------------------

    if start_time == "19:30":

        range_date = (
            pd.Timestamp(trading_date)
            - pd.Timedelta(days=1)
        ).date()

    else:

        range_date = trading_date

    range_data = get_session_data(
        range_date,
        start_time,
        end_time
    )

    if len(range_data) != 12:

        print(
            f"WARNING: {trading_date} {start_time}-{end_time} "
            f"has {len(range_data)} M5 candles instead of 12."
        )

        return None

    # --------------------------------------------------------
    # DR = CANDLE BODIES
    # --------------------------------------------------------

    dr_high = range_data["body_high"].max()
    dr_low = range_data["body_low"].min()

    # --------------------------------------------------------
    # IDR = WICKS
    # --------------------------------------------------------

    idr_high = range_data["high"].max()
    idr_low = range_data["low"].min()

    return {
        "dr_high": dr_high,
        "dr_low": dr_low,
        "dr_range": dr_high - dr_low,

        "idr_high": idr_high,
        "idr_low": idr_low,
        "idr_range": idr_high - idr_low
    }


# ============================================================
# GET LINES DATA
# ============================================================

def get_lines_data(
    trading_date,
    lines_start,
    lines_end,
    range_type
):

    # --------------------------------------------------------
    # ADR lines:
    #
    # Previous calendar day 20:30
    # →
    # Trading date 02:00
    # --------------------------------------------------------

    if range_type == "ADR":

        start = pd.Timestamp(
            f"{pd.Timestamp(trading_date).date()} "
            f"{lines_end}"
        )

        previous_date = (
            pd.Timestamp(trading_date)
            - pd.Timedelta(days=1)
        ).date()

        start = pd.Timestamp(
            f"{previous_date} {lines_start}"
        )

        end = pd.Timestamp(
            f"{trading_date} {lines_end}"
        )

    else:

        start = pd.Timestamp(
            f"{trading_date} {lines_start}"
        )

        end = pd.Timestamp(
            f"{trading_date} {lines_end}"
        )

    return m5.loc[
        (m5.index >= start) &
        (m5.index < end)
    ]


# ============================================================
# FIND FIRST CONFIRMATION
# ============================================================

def find_confirmation(
    trading_date,
    range_type,
    idr_high,
    idr_low
):

    settings = SESSIONS[range_type]

    lines_data = get_lines_data(
        trading_date,
        settings["lines_start"],
        settings["lines_end"],
        range_type
    )

    for timestamp, candle in lines_data.iterrows():

        close = candle["close"]

        # LONG
        if close > idr_high:

            return {
                "confirmed": True,
                "direction": "LONG",
                "confirmation_time": timestamp,
                "confirmation_price": close
            }

        # SHORT
        if close < idr_low:

            return {
                "confirmed": True,
                "direction": "SHORT",
                "confirmation_time": timestamp,
                "confirmation_price": close
            }

    return {
        "confirmed": False,
        "direction": None,
        "confirmation_time": None,
        "confirmation_price": None
    }


# ============================================================
# TEST TRADING DAY
# ============================================================

TEST_DATE = pd.Timestamp("2024-01-02").date()


# ============================================================
# PROCESS ALL THREE SESSIONS
# ============================================================

results = []


for range_type, settings in SESSIONS.items():

    range_values = calculate_range(
        TEST_DATE,
        settings["range_start"],
        settings["range_end"]
    )

    if range_values is None:
        continue

    confirmation = find_confirmation(
        TEST_DATE,
        range_type,
        range_values["idr_high"],
        range_values["idr_low"]
    )

    results.append({

        "trading_date": TEST_DATE,

        "range_type": range_type,

        "dr_high": range_values["dr_high"],
        "dr_low": range_values["dr_low"],
        "dr_range": range_values["dr_range"],

        "idr_high": range_values["idr_high"],
        "idr_low": range_values["idr_low"],
        "idr_range": range_values["idr_range"],

        "confirmed": confirmation["confirmed"],

        "direction": confirmation["direction"],

        "confirmation_time":
            confirmation["confirmation_time"],

        "confirmation_price":
            confirmation["confirmation_price"]
    })


# ============================================================
# DISPLAY
# ============================================================

results_df = pd.DataFrame(results)

print("\n======================================")
print("CORRECTED CONFIRMATION TEST")
print("======================================")

print(
    results_df.to_string(index=False)
)