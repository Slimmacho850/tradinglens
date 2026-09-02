import pandas as pd


# ==========================================
# TEST DR
# ==========================================

dr_high = 16674.229
dr_low = 16547.239

dr_range = dr_high - dr_low


# ==========================================
# FIBONACCI LEVELS
# ==========================================

fib_levels = [
    -2.0,
    -1.5,
    -1.0,
    -0.5,
    0.0,
    0.5,
    1.0,
    1.5,
    2.0,
    2.5,
    3.0
]


# ==========================================
# CALCULATE FROM HIGH → LOW
# ==========================================

results = []

for level in fib_levels:

    price = dr_high - (dr_range * level)

    results.append({
        "fib_level": level,
        "price": price,
        "distance_from_dr": abs(price - dr_high),
        "dr_multiple": abs(price - dr_high) / dr_range
    })


fib = pd.DataFrame(results)


# ==========================================
# DISPLAY
# ==========================================

print("\n======================================")
print("DR FIBONACCI LEVELS")
print("======================================")

print(
    fib.to_string(index=False)
)


print("\n======================================")
print("DR INFORMATION")
print("======================================")

print(f"DR High  : {dr_high}")
print(f"DR Low   : {dr_low}")
print(f"DR Range : {dr_range}")