# ml/ap_feature_schema.py
"""
R.O.O.K Feature Schema Contract v1.0
=====================================
This file defines the EXACT features and their ORDER that your XGBoost models
must be trained on. The ModelService uses this schema to build the inference
vector from incoming API requests.

!! DO NOT change feature names or order without retraining your models. !!
"""

# ─── Rainfall Prediction Features ────────────────────────────────────────────
# Train your xgb_rainfall.pkl with X = df[RAINFALL_FEATURES]
RAINFALL_FEATURES = [
    'month',           # int 1–12  : calendar month
    'day_of_year',     # int 1–365 : Julian day
    'lat',             # float     : station latitude (decimal degrees)
    'lng',             # float     : station longitude (decimal degrees)
    'elevation_m',     # float     : station elevation above sea level (m)
    'rain_lag1',       # float     : yesterday's rainfall (mm)
    'rain_lag2',       # float     : 2 days ago rainfall (mm)
    'rain_lag3',       # float     : 3 days ago rainfall (mm)
    'humidity',        # float     : relative humidity (%)
    'pressure_hpa',    # float     : sea-level pressure (hPa)
    'wind_kt',         # float     : wind speed (knots)
    'month_sin',       # float     : sin(2π×month/12) — circular seasonal encoding
    'month_cos',       # float     : cos(2π×month/12) — circular seasonal encoding
    # Optional INSAT features — set to 0 if unavailable:
    # 'olr',           # float     : Outgoing Longwave Radiation (W/m²) from INSAT-3D
]

# ─── Temperature Prediction Features ─────────────────────────────────────────
# Train your xgb_temperature.pkl with X = df[TEMPERATURE_FEATURES]
TEMPERATURE_FEATURES = [
    'month',           # int 1–12
    'day_of_year',     # int 1–365
    'lat',             # float
    'lng',             # float
    'elevation_m',     # float (m)
    'tmax_lag1',       # float : yesterday Tmax (°C)
    'tmin_lag1',       # float : yesterday Tmin (°C)
    'tmax_lag2',       # float : 2 days ago Tmax (°C)
    'tmin_lag2',       # float : 2 days ago Tmin (°C)
    'humidity',        # float : relative humidity (%)
    'pressure_hpa',    # float : sea-level pressure (hPa)
    'month_sin',       # float : sin(2π×month/12)
    'month_cos',       # float : cos(2π×month/12)
    # Optional INSAT features — set to 0 if unavailable:
    # 'lst',           # float : Land Surface Temperature from INSAT-3D (°C)
]

# ─── Default Values (used when a feature is unavailable in request) ───────────
FEATURE_DEFAULTS = {
    'month':        6,       # June (monsoon season)
    'day_of_year':  172,
    'lat':          15.9,    # AP centroid
    'lng':          79.7,
    'elevation_m':  200.0,
    'rain_lag1':    5.0,
    'rain_lag2':    3.0,
    'rain_lag3':    2.0,
    'humidity':     70.0,
    'pressure_hpa': 1009.0,
    'wind_kt':      12.0,
    'tmax_lag1':    33.0,
    'tmin_lag1':    24.0,
    'tmax_lag2':    33.0,
    'tmin_lag2':    24.0,
    'month_sin':    0.866,   # sin(2π×6/12)
    'month_cos':    -0.5,    # cos(2π×6/12)
    # Optional INSAT
    'olr':          230.0,
    'lst':          35.0,
}

# ─── AP Station Reference Data (elevation lookup by nearest lat/lng) ──────────
AP_STATION_ELEVATIONS = {
    'Visakhapatnam': (17.69,  83.22,  17),
    'Vijayawada':    (16.51,  80.62,  26),
    'Guntur':        (16.31,  80.45,  30),
    'Kakinada':      (16.98,  82.24,  10),
    'Rajahmundry':   (17.00,  81.77,  22),
    'Eluru':         (16.71,  81.10,  15),
    'Kurnool':       (15.83,  78.04,  268),
    'Anantapur':     (14.68,  77.60,  350),
    'Nellore':       (14.44,  79.98,  19),
    'Tirupati':      (13.63,  79.42,  162),
    'Chittoor':      (13.21,  79.10,  280),
    'Srikakulam':    (18.30,  83.90,  17),
    'YSR Kadapa':    (14.47,  78.82,  138),
}
