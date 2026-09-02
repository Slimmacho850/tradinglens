# ============================================================
# EXTENSION LOGIC CHECK
# ============================================================

# ODR example from our actual data

dr_high = 16847.799
dr_low = 16497.529
dr_range = 50.15

direction = "SHORT"

extension_price = 16628.979


print("\n======================================")
print("EXTENSION LOGIC CHECK")
print("======================================")

print("DR HIGH:", dr_high)
print("DR LOW:", dr_low)
print("DR RANGE:", dr_range)
print("DIRECTION:", direction)
print("EXTREME PRICE:", extension_price)


if direction == "LONG":

    extension_distance = max(
        0.0,
        extension_price - dr_high
    )

else:

    extension_distance = max(
        0.0,
        dr_low - extension_price
    )


extension_sd = (
    extension_distance / dr_range
)


print("\n======================================")
print("RESULT")
print("======================================")

print("EXTENSION DISTANCE:", extension_distance)
print("EXTENSION SD:", extension_sd)