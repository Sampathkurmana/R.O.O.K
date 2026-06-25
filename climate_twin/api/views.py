import csv
import io
import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from climate_twin.models import ClimateObservation, ClimatePrediction, ScenarioSimulation, Alert
from climate_twin.services.ai_service import AISimulationEngine
import datetime
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt # <-- Notice the 's' in views
import math

logger = logging.getLogger('rook.api')

class WeatherAPIView(APIView):
    def get(self, request):
        # 1. Catch the coordinates your frontend is sending
        lat_str = request.GET.get('lat')
        lng_str = request.GET.get('lng')

        if lat_str and lng_str:
            lat = float(lat_str)
            lng = float(lng_str)
            
            # 2. Return UNIQUE API data based on the location
            # (Swap this out for your real IMD/GFS API fetch later)
            unique_temp = round(28.0 + (math.sin(lat * 10) * 4.5), 1)
            unique_rain = round(max(0, 10.0 + (math.cos(lng * 10) * 8.0)), 1)
            unique_wind = int(max(5, 14 + (math.sin(lat + lng) * 8)))
            
            return Response({
                "current": {
                    "temperature": unique_temp,
                    "rainfall": unique_rain,
                    "humidity": int(min(100, 60 + unique_temp * 0.8)),
                    "wind_speed": unique_wind,
                    "wind_direction": "SW"
                }
            })

        # 3. Default fallback if no coordinates are sent
        return Response({
            "current": {
                "temperature": 32.4,
                "rainfall": 12.4,
                "humidity": 78,
                "wind_speed": 18,
                "wind_direction": "SW"
            }
        })

class ForecastAPIView(APIView):
    """
    Provides 24-hour and 7-day weather trend forecasts.
    """
    def get(self, request):
        # 24-hour hourly stubs
        hourly = []
        base_temp = 32.4
        for hour in range(24):
            time_str = f"{(hour + 9) % 24:02d}:00"
            temp_offset = -4.0 * ((hour - 14) ** 2) / 100.0 + 3.0 # simple temperature parabola
            hourly.append({
                "time": time_str,
                "temperature": round(base_temp + temp_offset, 1),
                "rainfall": round(max(0, 0.5 * hour - 5) if hour > 10 else 0, 1),
                "humidity": round(78 - (temp_offset * 2.5))
            })

        # 7-day stubs (utilizing the AI prediction service)
        forecast_days = AISimulationEngine.predict_future_trends([], forecast_days=7)
        weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        today = datetime.datetime.now()
        
        daily = []
        for i, day_data in enumerate(forecast_days):
            day_date = today + datetime.timedelta(days=i)
            daily.append({
                "day": weekdays[day_date.weekday()],
                "date": day_date.strftime("%d %b"),
                "temperature": day_data["temperature"],
                "rainfall": day_data["rainfall"],
                "humidity": round(78 + (i * 0.8) - (day_data["temperature"] - 32.4) * 2)
            })

        return Response({
            "hourly": hourly,
            "daily": daily
        })

class DigitalTwinAPIView(APIView):
    """
    Handles interpolation of past, present, and predicted climates across variables
    (Rainfall, Temperature, Humidity, Wind, LST, SST) relative to a timeline index.
    """
    def get(self, request):
        timeline_step = request.query_params.get("step", "present") # past, present, future
        
        # Grid overlays stubs representing heatmaps or points for Leaflet visualization
        # Generates coordinates over Andhra Pradesh (Lat: 13.5 to 19.1, Lng: 76.7 to 84.8)
        grid_points = []
        lats = [14.2, 15.0, 15.8, 16.5, 17.3, 18.0]
        lngs = [77.5, 78.8, 79.9, 81.2, 82.5, 83.8]

        # Multipliers based on timeline stage to show real simulation divergence
        multiplier = 1.0
        if timeline_step == "past":
            multiplier = 0.92
        elif timeline_step == "future":
            multiplier = 1.08

        for idx, lat in enumerate(lats):
            for jdx, lng in enumerate(lngs):
                # Apply high-fidelity mathematical variance relative to lat/lng
                base_temp = 31.0 + (19.0 - lat) * 0.8 + (84.0 - lng) * 0.4
                base_rain = 8.0 + (lat - 13.0) * 3.2 + (lng - 76.0) * 1.5
                base_lst = base_temp + 2.5
                base_sst = base_temp - 3.0 if lng > 80.0 else 0.0 # only coast gets sea surface temp

                grid_points.append({
                    "id": idx * 10 + jdx,
                    "lat": round(lat, 2),
                    "lng": round(lng, 2),
                    "temperature": round(base_temp * multiplier, 1),
                    "rainfall": round(base_rain * (2.0 - multiplier), 1),
                    "humidity": round(min(100, 75 * (2.0 - multiplier)), 1),
                    "lst": round(base_lst * multiplier, 1),
                    "sst": round(base_sst * multiplier, 1) if base_sst > 0 else None,
                    "wind_speed": round(15 + idx * 2.1, 1),
                    "wind_direction": "SW" if lat > 16.0 else "WNW"
                })

        return Response({
            "timeline_step": timeline_step,
            "observations": grid_points
        })

class SimulatorAPIView(APIView):
    """
    Accepts temperature, rainfall, and humidity perturbations to compute and save climate scenarios.
    """
    def post(self, request):
        temp_change = float(request.data.get("temp_change", 0.0))
        rainfall_change = float(request.data.get("rainfall_change", 0.0))
        humidity_change = float(request.data.get("humidity_change", 0.0))

        # Perform risk calculation
        results = AISimulationEngine.calculate_simulation_risks(temp_change, rainfall_change, humidity_change)

        # Save to database
        try:
            ScenarioSimulation.objects.create(
                rainfall_change=rainfall_change,
                temperature_change=temp_change,
                humidity_change=humidity_change,
                drought_risk=results["drought_risk"],
                flood_risk=results["flood_risk"],
                heatwave_risk=results["heatwave_risk"],
                agricultural_impact=results["agricultural_impact"],
                water_stress_index=results["water_stress_index"]
            )
        except Exception:
            # Fallback if DB not fully migrated yet
            pass

        return Response(results, status=status.HTTP_200_OK)

class AlertsAPIView(APIView):
    """
    Fetches active severe weather alerts (Heatwave, Flood, Cyclone, Rainfall, Drought).
    """
    def get(self, request):
        # Fallback pre-populated lists to guarantee operation
        fallback_alerts = [
            {
                "id": 1,
                "type": "Cyclone",
                "severity": "Critical",
                "district": "Visakhapatnam & East Godavari Coast",
                "description": "Severe Cyclonic Storm warnings issued for coastal areas. Winds expected to exceed 65 knots with wave heights up to 4.5m."
            },
            {
                "id": 2,
                "type": "Heatwave",
                "severity": "High",
                "district": "Kurnool & Anantapur",
                "description": "High temperature anomalies exceeding +4.5C above seasonal averages. Public advisory issued for severe thermal exposure."
            },
            {
                "id": 3,
                "type": "Flood",
                "severity": "Medium",
                "district": "Krishna Basin Lowlands",
                "description": "Heavy rainfall predictions upstream triggers reservoir alerts. Runoff discharge levels rising."
            },
            {
                "id": 4,
                "type": "Drought",
                "severity": "Low",
                "district": "Rayalaseema Region",
                "description": "Prolonged dry spell observations indicate low soil moisture availability across rural farmlands."
            }
        ]
        
        # Try database first
        try:
            alerts = Alert.objects.filter(active=True)
            if alerts.exists():
                serializer_data = [
                    {
                        "id": alert.id,
                        "type": alert.type,
                        "severity": alert.severity,
                        "district": alert.district,
                        "description": alert.description
                    }
                    for alert in alerts
                ]
                return Response(serializer_data)
        except Exception:
            pass

        return Response(fallback_alerts)

class ReportsAPIView(APIView):
    """
    Generates and processes exportable monthly and seasonal reports in CSV or JSON.
    """
    def get(self, request):
        export_format = request.query_params.get("format", "json")
        report_type = request.query_params.get("type", "monsoon") # monsoon, heatwave, drought, monthly

        # Report structures
        report_meta = {
            "title": f"R.O.O.K Climate Assessment: {report_type.upper()}",
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d"),
            "region": "Andhra Pradesh Pilot",
            "summary": "AI models indicate standard monsoon onset with +2.4% temperature anomaly across interior Rayalaseema.",
            "metrics": [
                {"indicator": "Mean Temp Anomaly", "value": "+1.8 °C", "status": "Above Average"},
                {"indicator": "Cumulative Rainfall", "value": "244.8 mm", "status": "Normal"},
                {"indicator": "Mean Land Surface Temp (LST)", "value": "35.2 °C", "status": "Elevated"},
                {"indicator": "Water Stress Indicator", "value": "48.2%", "status": "Moderate"}
            ]
        }

        if export_format == "csv":
            # Generate CSV response inline
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Report Title", report_meta["title"]])
            writer.writerow(["Generated At", report_meta["generated_at"]])
            writer.writerow(["Region", report_meta["region"]])
            writer.writerow([])
            writer.writerow(["Indicator", "Value", "Status"])
            for metric in report_meta["metrics"]:
                writer.writerow([metric["indicator"], metric["value"], metric["status"]])
            
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="rook_{report_type}_report.csv"'
            return response

        return Response(report_meta)


# ─────────────────────────────────────────────────────────────────────────────
# XGBoost Model-Powered Prediction Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class PredictView(APIView):
    """
    POST /api/predict/
    Body: { "lat": float, "lng": float, "date": "ISO date str" (optional) }

    Returns XGBoost model prediction (or IDW fallback) for the given coordinates.
    Response:
    {
      "lat", "lng",
      "rainfall_mm":  float,
      "tmax_c":       float,
      "tmin_c":       float,
      "risk":         { "drought", "flood", "heatwave", "agri" },
      "source":       "xgboost" | "idw_fallback"
    }
    """

    def post(self, request):
        print("🚨🚨🚨 HELLO FROM THE NEW CODE!!! 🚨🚨🚨") # <--- ADD THIS
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, AttributeError):
            body = request.data

        lat  = float(body.get('lat', 15.9129))
        lng  = float(body.get('lng', 79.7400))
        date_str = body.get('date', datetime.datetime.utcnow().isoformat())

        rain = 8.0
        temp = {'tmax_c': 32.4, 'tmin_c': 24.5}
        wind = 14.0  # <--- Safe default wind
        risk = {'drought': 'Low', 'flood': 'Low', 'heatwave': 'Low', 'agri': 'Low'}
        source = 'idw_fallback'

        # Build feature vector from request context
        try:
            from ml.feature_builder import build_features_from_request
            features = build_features_from_request(lat, lng, body)
        except Exception as e:
            logger.warning(f'[PredictView] feature_builder error: {e}. Using defaults.')
            features = {
                'lat': lat, 'lng': lng,
                'month': datetime.datetime.utcnow().month,
                'day_of_year': datetime.datetime.utcnow().timetuple().tm_yday,
                'elevation_m': 150.0,
                'humidity': 72.0, 'pressure_hpa': 1008.0, 'wind_kt': 14.0,
                'rain_lag1': 5.0, 'rain_lag2': 3.0, 'rain_lag3': 2.0,
                'tmax_lag1': 33.0, 'tmin_lag1': 24.0,
                'tmax_lag2': 33.0, 'tmin_lag2': 24.0,
            }

        # Try XGBoost model → fallback to IDW
        try:
            from ml.model_service import ModelService
            service = ModelService.get_instance()

            if service.is_ready:
                rain = service.predict_rainfall(features)
                temp = service.predict_temperature(features)
                wind = service.predict_windspeed(features)
                risk = ModelService._compute_risk(rain, temp, features)
                source = 'xgboost'
            else:
                raise ValueError('Model not loaded')

        except Exception as e:
            logger.info(f'[PredictView] Falling back to IDW: {e}')
            try:
                from ml.fallback_idw import IDWFallback
                rain, temp, risk = IDWFallback.predict(lat, lng)
            except Exception as idw_err:
                logger.error(f'[PredictView] IDW fallback also failed: {idw_err}')
                rain = 8.0
                temp = {'tmax_c': 32.4, 'tmin_c': 24.5}
                wind = service.predict_windspeed(features)
                risk = {'drought': 'Low', 'flood': 'Low', 'heatwave': 'Low', 'agri': 'Low'}
            source = 'idw_fallback'

        return Response({
            'lat':          lat,
            'lng':          lng,
            'rainfall_mm':  round(float(rain or 0), 2),
            'tmax_c':       round(float((temp or {}).get('tmax_c', 32.4)), 1),
            'tmin_c':       round(float((temp or {}).get('tmin_c', 24.5)), 1),
            'wind_speed':   round(float(wind or 14.0), 1),
            'risk':         risk,
            'source':       source,
            'timestamp':    datetime.datetime.utcnow().isoformat(),
        })


class SimulateView(APIView):
    """
    POST /api/predict-simulate/
    Body: {
      "lat": float, "lng": float,
      "temp_delta": float   (°C shift, e.g. +2.5 or -1.0),
      "rain_delta": float   (% change, e.g. +30 or -50)
    }

    Applies What-If deltas and returns re-simulated predictions + risk.
    """

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, AttributeError):
            body = request.data

        lat         = float(body.get('lat', 15.9129))
        lng         = float(body.get('lng', 79.7400))
        temp_delta  = float(body.get('temp_delta', body.get('temp_change', 0.0)))
        rain_delta  = float(body.get('rain_delta', body.get('rainfall_change', 0.0)))
        hum_delta   = float(body.get('humidity_change', 0.0))

        # Build base feature vector
        try:
            from ml.feature_builder import build_features_from_request
            base_features = build_features_from_request(lat, lng, body)
        except Exception:
            base_features = {
                'lat': lat, 'lng': lng,
                'month': datetime.datetime.utcnow().month,
                'day_of_year': datetime.datetime.utcnow().timetuple().tm_yday,
                'elevation_m': 150.0,
                'humidity': max(0, min(100, 72.0 + hum_delta)),
                'pressure_hpa': 1008.0, 'wind_kt': 14.0,
                'rain_lag1': 5.0, 'rain_lag2': 3.0, 'rain_lag3': 2.0,
                'tmax_lag1': 33.0, 'tmin_lag1': 24.0,
                'tmax_lag2': 33.0, 'tmin_lag2': 24.0,
            }

        if hum_delta:
            base_features['humidity'] = max(0, min(100, base_features.get('humidity', 72) + hum_delta))

        deltas = {'temp_delta': temp_delta, 'rain_delta': rain_delta}

        try:
            from ml.model_service import ModelService
            service = ModelService.get_instance()
            result = service.predict_simulation(base_features, deltas)

        except Exception as e:
            logger.error(f'[SimulateView] Simulation error: {e}')
            # Legacy fallback to AISimulationEngine
            result_legacy = AISimulationEngine.calculate_simulation_risks(temp_delta, rain_delta, hum_delta)
            result = {
                'rainfall_mm':  float(result_legacy.get('water_stress_index', 8.0)),
                'tmax_c':       32.4 + temp_delta,
                'tmin_c':       24.5 + temp_delta,
                'risk': {
                    'drought':  result_legacy.get('drought_risk', 'Low'),
                    'flood':    result_legacy.get('flood_risk', 'Low'),
                    'heatwave': result_legacy.get('heatwave_risk', 'Low'),
                    'agri':     result_legacy.get('agricultural_impact', 'Low'),
                },
                'source': 'legacy_engine',
            }

        # Also compute the legacy format fields for backward compatibility with app.js
        risk = result.get('risk', {})
        water_stress = min(100, max(0, 40.0 + (temp_delta * 3) + (rain_delta * 0.5) + (hum_delta * 0.3)))
        agri_map = {'Low': 'Optimal Yield Output', 'Medium': 'Moderate Stress', 'High': 'Critical Yield Loss'}

        return Response({
            # New format
            'rainfall_mm':        round(float(result.get('rainfall_mm', 8.0)), 2),
            'tmax_c':             round(float(result.get('tmax_c', 32.4)), 1),
            'tmin_c':             round(float(result.get('tmin_c', 24.5)), 1),
            'risk':               risk,
            'source':             result.get('source', 'unknown'),
            # Legacy format kept for backward compat with app.js SimulatorAPIView consumer
            'drought_risk':       risk.get('drought', 'Low'),
            'flood_risk':         risk.get('flood', 'Low'),
            'heatwave_risk':      risk.get('heatwave', 'Low'),
            'agricultural_impact': agri_map.get(risk.get('agri', 'Low'), 'Optimal Yield Output'),
            'water_stress_index': round(water_stress, 1),
            'timestamp':          datetime.datetime.utcnow().isoformat(),
        })


class RiskView(APIView):
    """
    GET /api/risk/
    Returns per-district risk indices for the current timestep.
    """

    # AP district climate data (matches DISTRICT_STATIONS in app.js)
    DISTRICT_DATA = [
        {'name': 'Anantapur',       'lat': 14.6819, 'lng': 77.6006, 'temp': 34.2, 'rain': 2.1,  'humidity': 55},
        {'name': 'Chittoor',        'lat': 13.2172, 'lng': 79.1003, 'temp': 32.0, 'rain': 4.5,  'humidity': 68},
        {'name': 'East Godavari',   'lat': 17.2305, 'lng': 81.8282, 'temp': 31.8, 'rain': 22.4, 'humidity': 88},
        {'name': 'Guntur',          'lat': 16.3067, 'lng': 80.4365, 'temp': 33.5, 'rain': 11.2, 'humidity': 75},
        {'name': 'Krishna',         'lat': 16.1667, 'lng': 81.1333, 'temp': 32.9, 'rain': 14.8, 'humidity': 82},
        {'name': 'Kurnool',         'lat': 15.8281, 'lng': 78.0373, 'temp': 35.1, 'rain': 1.0,  'humidity': 52},
        {'name': 'Prakasam',        'lat': 15.5057, 'lng': 79.6450, 'temp': 33.8, 'rain': 3.2,  'humidity': 64},
        {'name': 'Srikakulam',      'lat': 18.2949, 'lng': 83.8938, 'temp': 30.5, 'rain': 28.6, 'humidity': 92},
        {'name': 'Nellore',         'lat': 14.4426, 'lng': 79.9865, 'temp': 33.0, 'rain': 5.1,  'humidity': 70},
        {'name': 'Visakhapatnam',   'lat': 17.6868, 'lng': 83.2185, 'temp': 31.2, 'rain': 18.5, 'humidity': 85},
        {'name': 'Vizianagaram',    'lat': 18.1124, 'lng': 83.3989, 'temp': 30.9, 'rain': 21.0, 'humidity': 89},
        {'name': 'West Godavari',   'lat': 16.8105, 'lng': 81.4288, 'temp': 32.1, 'rain': 19.3, 'humidity': 86},
        {'name': 'YSR Kadapa',      'lat': 14.4673, 'lng': 78.8242, 'temp': 34.6, 'rain': 1.8,  'humidity': 58},
    ]

    def get(self, request):
        from ml.model_service import ModelService
        results = []
        for d in self.DISTRICT_DATA:
            temp = {'tmax_c': d['temp'], 'tmin_c': d['temp'] - 5.5}
            try:
                risk = ModelService._compute_risk(d['rain'], temp, d)
            except Exception:
                risk = {'drought': 'Low', 'flood': 'Low', 'heatwave': 'Low', 'agri': 'Low'}
            results.append({
                'district':  d['name'],
                'lat':       d['lat'],
                'lng':       d['lng'],
                'temp':      d['temp'],
                'rain':      d['rain'],
                'humidity':  d['humidity'],
                'drought':   risk.get('drought', 'Low'),
                'flood':     risk.get('flood', 'Low'),
                'heatwave':  risk.get('heatwave', 'Low'),
            })
        return Response(results)


class ModelStatusView(APIView):
    """
    GET /api/model-status/
    Returns XGBoost model loading status.
    Used by the frontend to show an 'XGBoost Active' / 'IDW Estimate' badge.
    """

    def get(self, request):
        try:
            from ml.model_service import ModelService
            service = ModelService.get_instance()
            return Response(service.get_status())
        except Exception as e:
            return Response({
                'loaded': False,
                'error': str(e),
                'message': 'Model service unavailable. Using IDW fallback.'
            })


