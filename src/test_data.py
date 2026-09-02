import pandas as pd

# Location of the CSV file
file_path = "data/DAT_ASCII_NSXUSD_M1_2024.csv"

# Column names
columns = [
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume"
]

# Read the CSV file
data = pd.read_csv(
    file_path,
    sep=";",
    header=None,
    names=columns
)

# Convert the datetime column
data["datetime"] = pd.to_datetime(
    data["datetime"],
    format="%Y%m%d %H%M%S"
)

# Convert numerical columns
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

# Display information
print("\n==============================")
print("FIRST 5 ROWS")
print("==============================")

print(data.head())

print("\n==============================")
print("COLUMN NAMES")
print("==============================")

print(data.columns.tolist())

print("\n==============================")
print("DATA SHAPE")
print("==============================")

print(data.shape)

print("\n==============================")
print("DATA TYPES")
print("==============================")

print(data.dtypes)

print("\n==============================")
print("LAST 5 ROWS")
print("==============================")

print(data.tail())