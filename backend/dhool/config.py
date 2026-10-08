"""Deployment-specific values. Change these, not the logic."""

TZ = "Asia/Kolkata"

# Roof defaults when the homeowner doesn't know them.
DEFAULT_TILT = 20.0      # degrees from horizontal
DEFAULT_AZIMUTH = 180.0  # degrees, 180 = facing south

TARIFF_RS = 7.0          # ₹ per kWh, for turning lost energy into money

# Physics.
INVERTER_EFFICIENCY = 0.96
TEMP_COEFF = -0.004      # power change per °C of cell temperature above 25 °C

# Simulated neighbourhood (centre of the cluster of homes).
SIM_LAT = 28.61
SIM_LON = 77.21
CLEAN_RAIN_MM = 5.0      # a day with this much rain washes the panels
HAZE_PM25 = 150.0        # µg/m³, daily mean above which haze starts cutting output
