import pandas as pd
from pathlib import Path


# ============================================================
# SETTINGS
# ============================================================

EVENT_FILE = "database/events_2024.csv"
M1_FILE = "data/DAT_ASCII_NSXUSD_M1_2024.csv"

TEST_DATE = "2024-01-02"
TEST_RANGE = "RDR"

OUTPUT_DIR = Path("database/distributions")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD EVENT
# ============================================================

print("Loading event database...")

events = pd.read_csv(EVENT_FILE)

events["trading_date"] = pd.to_datetime(
    events["trading_date"]
)

events["confirmation_time"] = pd.to_datetime(
    events["confirmation_time"],
    errors="coerce"
)

events["confirmed"] = (
    events["confirmed"]
    .astype(str)
    .str.lower()
    .eq("true")
)

event = events[
    (events["trading_date"] == pd.Timestamp(TEST_DATE))
    &
    (events["range_type"] == TEST_RANGE)
    &
    (events["confirmed"])
]

if event.empty:
    raise SystemExit("Test event not found.")

event = event.iloc[0]


# ============================================================
# EVENT INFORMATION
# ============================================================

direction = event["direction"]

dr_high = float(event["dr_high"])
dr_low = float(event["dr_low"])
dr_range = float(event["dr_range"])

confirmation_time = event["confirmation_time"]


print()
print("======================================")
print("RETRACEMENT EPISODE DEBUG")
print("======================================")

print(f"Trading Date : {TEST_DATE}")
print(f"Range Type   : {TEST_RANGE}")
print(f"Direction    : {direction}")
print(f"DR High      : {dr_high}")
print(f"DR Low       : {dr_low}")
print(f"DR Range     : {dr_range}")
print(f"Confirmation : {confirmation_time}")


# ============================================================
# LOAD M1
# ============================================================

print()
print("Loading M1 data...")

columns = [
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume"
]

m1 = pd.read_csv(
    M1_FILE,
    sep=";",
    header=None,
    names=columns
)

m1["datetime"] = pd.to_datetime(
    m1["datetime"],
    format="%Y%m%d %H%M%S",
    errors="coerce"
)

for col in [
    "open",
    "high",
    "low",
    "close",
    "volume"
]:
    m1[col] = pd.to_numeric(
        m1[col],
        errors="coerce"
    )

m1 = (
    m1
    .dropna()
    .sort_values("datetime")
)


# ============================================================
# CREATE M5
# ============================================================

print("Creating M5 data...")

m5 = (
    m1
    .set_index("datetime")
    .resample("5min")
    .agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    })
    .dropna()
    .reset_index()
)


# ============================================================
# TRADING DAY
# 6:00 PM → NEXT DAY 5:59 PM
# ============================================================

day_start = pd.Timestamp(
    f"{TEST_DATE} 18:00:00"
)

day_end = (
    day_start +
    pd.Timedelta(days=1)
)

day = m5[
    (m5["datetime"] >= day_start)
    &
    (m5["datetime"] < day_end)
].copy()


# ============================================================
# DIRECTIONAL EXTREME
# ============================================================

hod_row = day.loc[
    day["high"].idxmax()
]

lod_row = day.loc[
    day["low"].idxmin()
]

hod_time = hod_row["datetime"]
hod_price = hod_row["high"]

lod_time = lod_row["datetime"]
lod_price = lod_row["low"]


if direction == "LONG":

    extreme_type = "HOD"
    extreme_time = hod_time
    extreme_price = hod_price

else:

    extreme_type = "LOD"
    extreme_time = lod_time
    extreme_price = lod_price


print()
print("======================================")
print("DIRECTIONAL EXTREME")
print("======================================")

print(
    f"{extreme_type}: "
    f"{extreme_price} @ {extreme_time}"
)


# ============================================================
# ANALYSIS WINDOW
# ============================================================

analysis = day[
    (day["datetime"] > confirmation_time)
    &
    (day["datetime"] <= extreme_time)
].copy()


# ============================================================
# STATE MACHINE
# ============================================================

extension_seen = False
retracement_active = False

current_episode = None
episodes = []


for _, row in analysis.iterrows():

    timestamp = row["datetime"]

    high = float(row["high"])
    low = float(row["low"])

    close = float(row["close"])


    # ========================================================
    # LONG
    # ========================================================

    if direction == "LONG":

        # ----------------------------------------------------
        # EXTENSION
        # ----------------------------------------------------

        outside_extension = high > dr_high

        inside_dr = (
            low <= dr_high
            and high >= dr_low
        )

        if outside_extension:

            extension_seen = True


        # ----------------------------------------------------
        # RETRACEMENT START
        #
        # Price was extended above DR HIGH and comes back
        # into the DR.
        # ----------------------------------------------------

        if (
            extension_seen
            and not retracement_active
            and inside_dr
            and low < dr_high
        ):

            retracement_active = True

            current_episode = {
                "direction": "LONG",
                "start_time": timestamp,
                "deepest_time": timestamp,
                "start_price": low,
                "deepest_price": low,
                "deepest_retracement": (
                    (dr_high - low)
                    / dr_range
                )
            }


        # ----------------------------------------------------
        # RETRACEMENT CONTINUES
        # ----------------------------------------------------

        elif retracement_active:

            retracement = (
                (dr_high - low)
                / dr_range
            )

            retracement = max(
                0.0,
                min(1.0, retracement)
            )

            if (
                retracement
                >
                current_episode[
                    "deepest_retracement"
                ]
            ):

                current_episode[
                    "deepest_retracement"
                ] = retracement

                current_episode[
                    "deepest_price"
                ] = low

                current_episode[
                    "deepest_time"
                ] = timestamp


            # ------------------------------------------------
            # RETRACEMENT ENDS
            #
            # Price leaves DR upward again.
            # ------------------------------------------------

            if close > dr_high:

                current_episode["end_time"] = timestamp

                episodes.append(
                    current_episode
                )

                current_episode = None

                retracement_active = False


    # ========================================================
    # SHORT
    # ========================================================

    elif direction == "SHORT":

        # ----------------------------------------------------
        # EXTENSION
        # ----------------------------------------------------

        outside_extension = low < dr_low

        inside_dr = (
            high >= dr_low
            and low <= dr_high
        )

        if outside_extension:

            extension_seen = True


        # ----------------------------------------------------
        # RETRACEMENT START
        #
        # Price was extended below DR LOW and comes back
        # into the DR.
        # ----------------------------------------------------

        if (
            extension_seen
            and not retracement_active
            and inside_dr
            and high > dr_low
        ):

            retracement_active = True

            current_episode = {
                "direction": "SHORT",
                "start_time": timestamp,
                "deepest_time": timestamp,
                "start_price": high,
                "deepest_price": high,
                "deepest_retracement": (
                    (high - dr_low)
                    / dr_range
                )
            }


        # ----------------------------------------------------
        # RETRACEMENT CONTINUES
        # ----------------------------------------------------

        elif retracement_active:

            retracement = (
                (high - dr_low)
                / dr_range
            )

            retracement = max(
                0.0,
                min(1.0, retracement)
            )

            if (
                retracement
                >
                current_episode[
                    "deepest_retracement"
                ]
            ):

                current_episode[
                    "deepest_retracement"
                ] = retracement

                current_episode[
                    "deepest_price"
                ] = high

                current_episode[
                    "deepest_time"
                ] = timestamp


            # ------------------------------------------------
            # RETRACEMENT ENDS
            #
            # Price leaves DR downward again.
            # ------------------------------------------------

            if close < dr_low:

                current_episode["end_time"] = timestamp

                episodes.append(
                    current_episode
                )

                current_episode = None

                retracement_active = False


# ============================================================
# CLOSE FINAL EPISODE
# ============================================================

if current_episode is not None:

    current_episode["end_time"] = extreme_time

    episodes.append(
        current_episode
    )


# ============================================================
# EPISODE RESULTS
# ============================================================

episode_df = pd.DataFrame(
    episodes
)


print()
print("======================================")
print("RETRACEMENT EPISODES")
print("======================================")


if episode_df.empty:

    print(
        "No retracement episodes detected."
    )

else:

    episode_df[
        "retracement_percent"
    ] = (
        episode_df[
            "deepest_retracement"
        ] * 100
    )

    print(
        episode_df[
            [
                "direction",
                "start_time",
                "deepest_time",
                "end_time",
                "deepest_price",
                "retracement_percent"
            ]
        ].to_string(
            index=False
        )
    )


# ============================================================
# MAXIMUM RETRACEMENT
# ============================================================

print()
print("======================================")
print("MAXIMUM RETRACEMENT BEFORE EXTREME")
print("======================================")


if episode_df.empty:

    print(
        "No valid retracement detected."
    )

else:

    max_index = (
        episode_df[
            "deepest_retracement"
        ].idxmax()
    )

    maximum = episode_df.loc[
        max_index
    ]

    print(
        f"Extreme Type       : {extreme_type}"
    )

    print(
        f"Maximum Retracement: "
        f"{maximum['retracement_percent']:.4f}%"
    )

    print(
        f"Deepest Price      : "
        f"{maximum['deepest_price']}"
    )

    print(
        f"Deepest Time       : "
        f"{maximum['deepest_time']}"
    )


# ============================================================
# SAVE
# ============================================================

output_file = (
    OUTPUT_DIR /
    "debug_retracement_episodes.csv"
)

episode_df.to_csv(
    output_file,
    index=False
)


print()
print("======================================")
print("DEBUG COMPLETE")
print("======================================")

print(
    f"Saved to: {output_file}"
)