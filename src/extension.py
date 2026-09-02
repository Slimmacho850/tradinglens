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
# LOAD M1
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

for column in [
    "open",
    "high",
    "low",
    "close",
    "volume"
]:

    m1[column] = pd.to_numeric(
        m1[column],
        errors="coerce"
    )

m1 = m1.dropna()

m1 = m1.sort_values("datetime")

m1 = m1.set_index("datetime")


# ============================================================
# M1 → M5
# ============================================================

m5 = m1.resample("5min").agg({

    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"

})

m5 = m5.dropna()


# ============================================================
# DR BODY
# ============================================================

m5["body_high"] = m5[["open", "close"]].max(axis=1)

m5["body_low"] = m5[["open", "close"]].min(axis=1)


# ============================================================
# GET RANGE DATA
# ============================================================

def get_range_data(trading_date, range_type):

    settings = SESSIONS[range_type]

    if range_type == "ADR":

        range_date = (
            pd.Timestamp(trading_date)
            - pd.Timedelta(days=1)
        ).date()

    else:

        range_date = trading_date

    start = pd.Timestamp(
        f"{range_date} {settings['range_start']}"
    )

    end = pd.Timestamp(
        f"{range_date} {settings['range_end']}"
    )

    return m5.loc[
        (m5.index >= start) &
        (m5.index < end)
    ]


# ============================================================
# GET LINES DATA
# ============================================================

def get_lines_data(trading_date, range_type):

    settings = SESSIONS[range_type]

    if range_type == "ADR":

        previous_date = (
            pd.Timestamp(trading_date)
            - pd.Timedelta(days=1)
        ).date()

        start = pd.Timestamp(
            f"{previous_date} {settings['lines_start']}"
        )

        end = pd.Timestamp(
            f"{trading_date} {settings['lines_end']}"
        )

    else:

        start = pd.Timestamp(
            f"{trading_date} {settings['lines_start']}"
        )

        end = pd.Timestamp(
            f"{trading_date} {settings['lines_end']}"
        )

    return m5.loc[
        (m5.index >= start) &
        (m5.index < end)
    ]


# ============================================================
# CALCULATE DR
# ============================================================

def calculate_dr(range_data):

    dr_high = range_data["body_high"].max()

    dr_low = range_data["body_low"].min()

    dr_range = dr_high - dr_low

    return dr_high, dr_low, dr_range


# ============================================================
# CALCULATE IDR
# ============================================================

def calculate_idr(range_data):

    idr_high = range_data["high"].max()

    idr_low = range_data["low"].min()

    return idr_high, idr_low


# ============================================================
# FIND FIRST CONFIRMATION
# ============================================================

def find_confirmation(
    lines_data,
    idr_high,
    idr_low
):

    for timestamp, candle in lines_data.iterrows():

        close = candle["close"]

        # -----------------------------------------------
        # LONG
        # -----------------------------------------------

        if close > idr_high:

            return {
                "direction": "LONG",
                "time": timestamp,
                "price": close
            }

        # -----------------------------------------------
        # SHORT
        # -----------------------------------------------

        if close < idr_low:

            return {
                "direction": "SHORT",
                "time": timestamp,
                "price": close
            }

    return None


# ============================================================
# CALCULATE MAXIMUM EXTENSION
# ============================================================

def calculate_max_extension(
    lines_data,
    confirmation,
    dr_high,
    dr_low,
    dr_range
):

    # ========================================================
    # ONLY CANDLES AFTER CONFIRMATION
    # ========================================================

    post_confirmation = lines_data.loc[
        lines_data.index > confirmation["time"]
    ]

    if post_confirmation.empty:

        return {
            "maximum_extension": 0.0,
            "extension_price": None,
            "extension_time": None
        }


    # ========================================================
    # LONG
    # ========================================================

    if confirmation["direction"] == "LONG":

        highest_price = post_confirmation["high"].max()

        extension_distance = max(
            0.0,
            highest_price - dr_high
        )

        maximum_extension = (
            extension_distance / dr_range
        )

        extension_time = (
            post_confirmation["high"].idxmax()
        )

        extension_price = highest_price


    # ========================================================
    # SHORT
    # ========================================================

    else:

        lowest_price = post_confirmation["low"].min()

        extension_distance = max(
            0.0,
            dr_low - lowest_price
        )

        maximum_extension = (
            extension_distance / dr_range
        )

        extension_time = (
            post_confirmation["low"].idxmin()
        )

        extension_price = lowest_price


    return {

        "maximum_extension":
            maximum_extension,

        "extension_price":
            extension_price,

        "extension_time":
            extension_time
    }


# ============================================================
# TEST
# ============================================================

results = []


for range_type in SESSIONS:

    # --------------------------------------------------------
    # RANGE
    # --------------------------------------------------------

    range_data = get_range_data(
        TEST_DATE,
        range_type
    )

    print(
        f"\n{range_type} range candles: "
        f"{len(range_data)}"
    )

    if len(range_data) != 12:

        print(
            f"WARNING: {range_type} does not "
            f"contain exactly 12 M5 candles."
        )

        continue


    # --------------------------------------------------------
    # DR
    # --------------------------------------------------------

    dr_high, dr_low, dr_range = calculate_dr(
        range_data
    )


    # --------------------------------------------------------
    # IDR
    # --------------------------------------------------------

    idr_high, idr_low = calculate_idr(
        range_data
    )


    # --------------------------------------------------------
    # LINES
    # --------------------------------------------------------

    lines_data = get_lines_data(
        TEST_DATE,
        range_type
    )


    # --------------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------------

    confirmation = find_confirmation(
        lines_data,
        idr_high,
        idr_low
    )


    if confirmation is None:

        results.append({

            "trading_date": TEST_DATE,
            "range_type": range_type,

            "dr_high": dr_high,
            "dr_low": dr_low,
            "dr_range": dr_range,

            "idr_high": idr_high,
            "idr_low": idr_low,

            "confirmed": False,
            "direction": None,

            "confirmation_time": None,
            "confirmation_price": None,

            "maximum_extension": None,
            "extension_price": None,
            "extension_time": None
        })

        continue


    # --------------------------------------------------------
    # EXTENSION
    # --------------------------------------------------------
    print("\nDEBUG:", range_type)
print("DR HIGH:", dr_high)
print("DR LOW:", dr_low)
print("DR RANGE:", dr_range)
print("DIRECTION:", confirmation["direction"])
print("CONFIRMATION:", confirmation["price"])

if confirmation["direction"] == "SHORT":
    print(
        "EXPECTED SHORT EXTENSION:",
        max(0, dr_low - lines_data.loc[
            lines_data.index > confirmation["time"]
        ]["low"].min())
    )
    extension = calculate_max_extension(

        lines_data,

        confirmation,

        dr_high,
        dr_low,

        dr_range
    )


    results.append({

        "trading_date": TEST_DATE,
        "range_type": range_type,

        "dr_high": dr_high,
        "dr_low": dr_low,
        "dr_range": dr_range,

        "idr_high": idr_high,
        "idr_low": idr_low,

        "confirmed": True,

        "direction":
            confirmation["direction"],

        "confirmation_time":
            confirmation["time"],

        "confirmation_price":
            confirmation["price"],

        "maximum_extension":
            extension["maximum_extension"],

        "extension_price":
            extension["extension_price"],

        "extension_time":
            extension["extension_time"]
    })


# ============================================================
# DISPLAY
# ============================================================

results_df = pd.DataFrame(results)


print("\n")
print("======================================")
print("EXTENSION TEST")
print("======================================")

print(
    results_df.to_string(index=False)
)