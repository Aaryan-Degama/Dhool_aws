"""Deployment-specific values. Change these, not the logic."""

TZ = "Asia/Kolkata"

# Roof defaults when the homeowner doesn't know them.
DEFAULT_TILT = 20.0  # degrees from horizontal
DEFAULT_AZIMUTH = 180.0  # degrees, 180 = facing south

TARIFF_RS = 7.0  # ₹ per kWh, for turning lost energy into money
WASH_COST_RS = 50.0  # what one wash costs the household in water and effort; a paid cleaner is ₹200 to ₹300
# A dust storm is dusty air, strong gusts and lost visibility in the same hour (the app's sandstorm sky uses
# the same three). Dust alone is not one: Delhi's air carries 300 µg/m³ on a calm clear night.
STORM_DUST, STORM_GUST_KMH, STORM_VISIBILITY_M = 150.0, 40.0, 5000.0
DRY_SPELL_DAYS = 30  # with no rain or dust storm in the forecast, a wash is taken to keep paying this long

# Physics.
INVERTER_EFFICIENCY = 0.96
TEMP_COEFF = -0.004  # power change per °C of cell temperature above 25 °C

# Simulated neighbourhood (centre of the cluster of homes).
SIM_LAT = 28.61
SIM_LON = 77.21
CLEAN_RAIN_MM = 5.0  # a day with this much rain washes the panels
HAZE_PM25 = 150.0  # µg/m³, daily mean above which haze starts cutting output
