import pandas as pd

# ==========================================
# 1. FILE LOCATION
# ==========================================

file_path = "data/DAT_ASCII_NSXUSD_M1_2024.csv"


# ==========================================
# 2. READ THE M1 DATA
# ==========================================

columns = [
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume"
]

data = pd.read_csv(
    file_path,
    sep=";",
    header=None,
    names=columns
)


# ==========================================
# 3. CONVERT DATA TYPES
# ==========================================

data["datetime"] = pd.to_datetime(
    data["datetime"],
    format="%Y%m%d %H%M%S"
)

numeric_columns = [
    "open",
    "high",
    "low",
    "close",
    "volume"
]

for column in numeric_columns:
    data[column] = pd.to_numeric(
        data[column],
        errors="coerce"
    )


# ==========================================
# 4. SORT BY TIME
# ==========================================

data = data.sort_values("datetime")

# Make datetime the index
data = data.set_index("datetime")


# ==========================================
# 5. CONVERT M1 → M5
# ==========================================

m5 = data.resample("5min").agg({
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"
})


# ==========================================
# 6. REMOVE EMPTY CANDLES
# ==========================================

m5 = m5.dropna()


# ==========================================
# 7. RESET INDEX
# ==========================================

m5 = m5.reset_index()


# ==========================================
# 8. DISPLAY RESULTS
# ==========================================

print("\n==============================")
print("M5 FIRST 10 CANDLES")
print("==============================")

print(m5.head(10))


print("\n==============================")
print("M5 DATA SHAPE")
print("==============================")

print(m5.shape)


print("\n==============================")
print("M5 LAST 10 CANDLES")
print("==============================")

print(m5.tail(10))