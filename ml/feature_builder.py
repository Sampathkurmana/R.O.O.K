"""
ml/feature_builder.py
======================
Builds the feature dict for model inference from incoming API request data.
Handles date parsing, lag feature lookup, and elevation resolution.
"""

import math
from datetime import datetime, timedelta
from ml.ap_feature_schema import FEATURE_DEFAULTS, AP_STATION_ELEVATIONS


def build_features_from_request(lat: float, lng: float, request_data: dict) -> dict:
    """
    Build a complete feature dict from an API request.
    
    Args:
        lat: Clicked latitude
        lng: Clicked longitude
        request_data: Dict from POST body (may include 'date', 'features')
    
    Returns:
        Feature dict with all keys from RAINFALL_FEATURES and TEMPERATURE_FEATURES
    """
    # Parse date
    date_str = request_data.get('date', datetime.utcnow().isoformat())
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        dt = datetime.utcnow()

    month      = dt.month
    day_of_year = dt.timetuple().tm_yday

    # Resolve elevation from nearest known station
    elevation_m = _nearest_elevation(lat, lng)

    # Seasonal encoding
    month_sin = math.sin(2 * math.pi * month / 12)
    month_cos = math.cos(2 * math.pi * month / 12)

    # If caller provides explicit features (e.g., from live IMD API), use them.
    # Otherwise, use realistic AP climatological defaults.
    explicit = request_data.get('features', {})

    features = {
        # Temporal
        'month':       explicit.get('month',      month),
        'day_of_year': explicit.get('day_of_year', day_of_year),

        # Spatial
        'lat':         lat,
        'lng':         lng,
        'elevation_m': explicit.get('elevation_m', elevation_m),

        # Rainfall lag features
        'rain_lag1':   explicit.get('rain_lag1', FEATURE_DEFAULTS['rain_lag1']),
        'rain_lag2':   explicit.get('rain_lag2', FEATURE_DEFAULTS['rain_lag2']),
        'rain_lag3':   explicit.get('rain_lag3', FEATURE_DEFAULTS['rain_lag3']),

        # Met observations
        'humidity':     explicit.get('humidity',    FEATURE_DEFAULTS['humidity']),
        'pressure_hpa': explicit.get('pressure_hpa', FEATURE_DEFAULTS['pressure_hpa']),
        'wind_kt':      explicit.get('wind_kt',     FEATURE_DEFAULTS['wind_kt']),

        # Temperature lag features
        'tmax_lag1':   explicit.get('tmax_lag1', FEATURE_DEFAULTS['tmax_lag1']),
        'tmin_lag1':   explicit.get('tmin_lag1', FEATURE_DEFAULTS['tmin_lag1']),
        'tmax_lag2':   explicit.get('tmax_lag2', FEATURE_DEFAULTS['tmax_lag2']),
        'tmin_lag2':   explicit.get('tmin_lag2', FEATURE_DEFAULTS['tmin_lag2']),

        # Seasonal encodings (always computed fresh)
        'month_sin': month_sin,
        'month_cos': month_cos,

        # Optional INSAT features
        'olr': explicit.get('olr', FEATURE_DEFAULTS['olr']),
        'lst': explicit.get('lst', FEATURE_DEFAULTS['lst']),
    }

    return features


def _nearest_elevation(lat: float, lng: float) -> float:
    """
    Return elevation (m) by finding the nearest AP station.
    Falls back to 200m (AP average) if no close match.
    """
    best_dist = float('inf')
    best_elev = 200.0

    for name, (s_lat, s_lng, elev) in AP_STATION_ELEVATIONS.items():
        dist = (lat - s_lat) ** 2 + (lng - s_lng) ** 2
        if dist < best_dist:
            best_dist = dist
            best_elev = float(elev)

    return best_elev


def build_features_for_simulation(lat: float, lng: float, deltas: dict) -> dict:
    """
    Build feature dict for a what-if simulation request.
    Applies temperature and rainfall deltas to the base climatological values.
    """
    base = build_features_from_request(lat, lng, {})

    if 'temp_delta' in deltas:
        d = float(deltas['temp_delta'])
        base['tmax_lag1'] += d
        base['tmin_lag1'] += d
        base['tmax_lag2'] += d
        base['tmin_lag2'] += d

    if 'rain_delta' in deltas:
        factor = 1.0 + (float(deltas['rain_delta']) / 100.0)
        for lag in ['rain_lag1', 'rain_lag2', 'rain_lag3']:
            base[lag] = max(0.0, base[lag] * factor)

    return base
