"""
ml/fallback_idw.py
===================
IDW (Inverse Distance Weighting) spatial interpolation fallback.
Used when XGBoost models are not yet loaded.
Produces plausible values from the 13 AP AWS stations so the UI
continues to function normally before the real model is integrated.
"""

import math

# Reference AWS station data (climatological normals for AP)
# These mirror DISTRICT_STATIONS in app.js
_AP_STATIONS = [
    {'name': 'Visakhapatnam', 'lat': 17.69, 'lng': 83.22, 'temp': 31.2, 'rain': 18.5, 'humidity': 76, 'wind': 15, 'pressure': 1007},
    {'name': 'Vijayawada',    'lat': 16.51, 'lng': 80.62, 'temp': 33.8, 'rain': 4.2,  'humidity': 65, 'wind': 10, 'pressure': 1008},
    {'name': 'Guntur',        'lat': 16.31, 'lng': 80.45, 'temp': 33.5, 'rain': 5.1,  'humidity': 67, 'wind': 11, 'pressure': 1008},
    {'name': 'Kakinada',      'lat': 16.98, 'lng': 82.24, 'temp': 31.8, 'rain': 22.4, 'humidity': 78, 'wind': 14, 'pressure': 1007},
    {'name': 'Rajahmundry',   'lat': 17.00, 'lng': 81.77, 'temp': 32.1, 'rain': 12.3, 'humidity': 72, 'wind': 12, 'pressure': 1008},
    {'name': 'Eluru',         'lat': 16.71, 'lng': 81.10, 'temp': 32.8, 'rain': 8.7,  'humidity': 70, 'wind': 10, 'pressure': 1008},
    {'name': 'Kurnool',       'lat': 15.83, 'lng': 78.04, 'temp': 35.1, 'rain': 1.0,  'humidity': 55, 'wind': 14, 'pressure': 1009},
    {'name': 'Anantapur',     'lat': 14.68, 'lng': 77.60, 'temp': 34.2, 'rain': 2.1,  'humidity': 52, 'wind': 16, 'pressure': 1009},
    {'name': 'Nellore',       'lat': 14.44, 'lng': 79.98, 'temp': 33.0, 'rain': 6.5,  'humidity': 70, 'wind': 12, 'pressure': 1008},
    {'name': 'Tirupati',      'lat': 13.63, 'lng': 79.42, 'temp': 32.5, 'rain': 5.8,  'humidity': 68, 'wind': 11, 'pressure': 1009},
    {'name': 'Chittoor',      'lat': 13.21, 'lng': 79.10, 'temp': 33.1, 'rain': 3.4,  'humidity': 62, 'wind': 10, 'pressure': 1009},
    {'name': 'Srikakulam',    'lat': 18.30, 'lng': 83.90, 'temp': 30.8, 'rain': 20.1, 'humidity': 80, 'wind': 16, 'pressure': 1007},
    {'name': 'YSR Kadapa',    'lat': 14.47, 'lng': 78.82, 'temp': 34.6, 'rain': 1.8,  'humidity': 58, 'wind': 13, 'pressure': 1009},
]


class IDWFallback:
    """
    Spatial interpolation fallback using Inverse Distance Weighting.
    Called automatically by ModelService when XGBoost models are not loaded.
    """

    @staticmethod
    def predict(lat: float, lng: float) -> tuple:
        """
        Returns (rainfall_mm, temp_dict, risk_dict) via IDW from 13 AP stations.
        
        Args:
            lat: target latitude
            lng: target longitude
        
        Returns:
            (float rainfall_mm, {'tmax_c': float, 'tmin_c': float}, {'drought':..., 'flood':..., 'heatwave':...})
        """
        rain, temp, humidity, pressure, wind = IDWFallback._idw_all(lat, lng)

        tmax = temp
        tmin = temp - 5.5

        risk = IDWFallback._compute_risk(rain, tmax)

        return (
            round(rain, 2),
            {'tmax_c': round(tmax, 1), 'tmin_c': round(tmin, 1)},
            risk
        )

    @staticmethod
    def _idw_all(lat: float, lng: float) -> tuple:
        """IDW interpolation for all fields from station data."""
        total_weight = 0.0
        rain = temp = humidity = pressure = wind = 0.0

        for s in _AP_STATIONS:
            dlat = lat - s['lat']
            dlng = lng - s['lng']
            dist2 = dlat * dlat + dlng * dlng
            w = 1e12 if dist2 < 1e-5 else 1.0 / (dist2 * dist2)
            total_weight += w
            rain     += w * s['rain']
            temp     += w * s['temp']
            humidity += w * s['humidity']
            pressure += w * s['pressure']
            wind     += w * s['wind']

        if total_weight == 0:
            return (5.0, 33.0, 65.0, 1008.0, 12.0)

        return (
            rain     / total_weight,
            temp     / total_weight,
            humidity / total_weight,
            pressure / total_weight,
            wind     / total_weight,
        )

    @staticmethod
    def _compute_risk(rain: float, tmax: float) -> dict:
        drought  = 'High' if rain < 1.0 and tmax > 38 else ('Medium' if rain < 3.0 and tmax > 36 else 'Low')
        flood    = 'High' if rain > 50   else ('Medium' if rain > 25 else 'Low')
        heatwave = ('Extreme' if tmax > 42 else ('High' if tmax > 40 else ('Medium' if tmax > 37 else 'Low')))
        agri     = 'High' if drought == 'High' or heatwave in ('High', 'Extreme') else ('Medium' if drought == 'Medium' else 'Low')
        return {'drought': drought, 'flood': flood, 'heatwave': heatwave, 'agri': agri}
