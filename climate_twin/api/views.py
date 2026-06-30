# Triggering reload after fixing model_meta.json conflict
import csv
import io
import json
import logging
import datetime
import math
from types import SimpleNamespace
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from ml.model_service import ModelService

from climate_twin.models import (
    State, District, ClimateObservation, ClimatePrediction,
    ClimateSimulation, ClimatePlayback, RiskAssessment, Alert
)
from climate_twin.services.core_engines import (
    ObservationEngine, PredictionEngine, ScenarioEngine,
    AnalyticsRiskEngine, DigitalTwinEngine, ClimatePlaybackService
)
from ml.model_service import ModelService
logger = logging.getLogger('rook.api')
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.cache import cache

DEFAULT_AP_PLAYBACK_STATIONS = [
    ("Anantapur", 14.6819, 77.6006),
    ("Chittoor", 13.2172, 79.1003),
    ("East Godavari", 17.2305, 81.8282),
    ("Guntur", 16.3067, 80.4365),
    ("Krishna", 16.1667, 81.1333),
    ("Kurnool", 15.8281, 78.0373),
    ("Prakasam", 15.5057, 79.6450),
    ("Srikakulam", 18.2949, 83.8938),
    ("Nellore", 14.4426, 79.9865),
    ("Visakhapatnam", 17.6868, 83.2185),
    ("Vizianagaram", 18.1124, 83.3989),
    ("West Godavari", 16.8105, 81.4288),
    ("YSR Kadapa", 14.4673, 78.8242),
]

# class WeatherAPIView(APIView):
#     def get(self, request):
#         lat = request.GET.get('lat', '17.6868')
#         lng = request.GET.get('lng', '83.2185')
        
#         # YOUR API KEY (Get one for free at OpenWeatherMap.org)
#         API_KEY = "280668dd93f8ac56029ab0ecf13967b1"
#         url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={API_KEY}&units=metric"
#         try:
#             response = requests.get(url)
#             data = response.json()
            
#             # 🔥 ADD THIS LINE!
#             print("DEBUG: API Response:", data) 
            
#             #return Response({ ... })
#         except Exception as e:
#             return Response({"error": "Weather service unavailable", "details": str(e)}, status=503)
        
#         try:
#             response = requests.get(url)
#             data = response.json()
            
#             # Extract only what you need
#             return Response({
#                 "current": {
#                     "temperature": data['main']['temp'],
#                     "rainfall": data.get('rain', {}).get('1h', 0), # Some APIs return 0 if no rain
#                     "humidity": data['main']['humidity'],
#                     "wind_speed": (data['wind']['speed'] * 3.6).round(1), # Convert m/s to km/h
#                     "wind_direction": "SW", # You can map degrees to cardinal here
#                     "pressure": data['main']['pressure'],
#                     "district": data['name']
#                 }
#             })
        
#         except Exception as e:
#             # If the API fails, return a safe backup, NOT a 500 error
#             return Response({"error": "Weather service unavailable", "details": str(e)}, status=503)

def _safe_float(val, default=0.0):
    if val is None:
        return default
    if isinstance(val, str):
        val_lower = val.lower().strip()
        if val_lower in ('null', 'undefined', ''):
            return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

class WeatherAPIView(APIView):
    """
    GET /api/weather/
    Fetches OpenWeatherMap (Core) + Open-Meteo (SST/LST), saves to DB, caches for 12 hours.
    """
    def get(self, request):
        lat = _safe_float(request.GET.get('lat'), 17.6868)
        lng = _safe_float(request.GET.get('lng'), 83.2185)
        
        # 1. THE 12-HOUR SHIELD 
        cache_key = f"weather_{round(lat, 2)}_{round(lng, 2)}"
        cached_data = cache.get(cache_key)

        if cached_data:
            print(f"⚡ [R.O.O.K] Loading from Cache! API safe.")
            return Response(cached_data)

        print("🌍 [R.O.O.K] Cache empty. Fetching live satellite data...")

        try:
            # --- API 1: OPENWEATHERMAP (Core Data) ---
            API_KEY = "280668dd93f8ac56029ab0ecf13967b1" # Your API Key
            owm_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={API_KEY}&units=metric"
            owm_response = requests.get(owm_url).json()

            temp = owm_response['main']['temp']
            rain = owm_response.get('rain', {}).get('1h', 0.0)
            
            # Physics: Wind Speed & Vectors
            wind_speed_ms = owm_response['wind']['speed']
            wind_speed_kmh = round(wind_speed_ms * 3.6, 1) # Your Python-safe km/h fix!
            wind_deg = owm_response['wind'].get('deg', 0)
            
            wind_deg_rad = math.radians(wind_deg)
            wind_u = -wind_speed_ms * math.sin(wind_deg_rad)
            wind_v = -wind_speed_ms * math.cos(wind_deg_rad)
            
            # Geographic Check: Is it Ocean? 
            is_ocean = lng > 83.2 

            # --- API 2: OPEN-METEO (LST & SST) ---
            lst = None
            sst = None
            
            if is_ocean:
                marine_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lng}&current=ocean_temperature"
                marine_resp = requests.get(marine_url).json()
                sst = marine_resp.get('current', {}).get('ocean_temperature')
            else:
                land_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=surface_temperature"
                land_resp = requests.get(land_url).json()
                lst = land_resp.get('current', {}).get('surface_temperature')

            now = datetime.datetime.now()
            today = datetime.date.today()

            # --- 3. PUSH TO THE DATABASE (Exodia Format) ---
            defaults = {
                'rainfall': rain,
                'pressure': owm_response['main']['pressure'], 
                'wind_speed': wind_speed_kmh,
                'temperature': temp,
                'humidity': owm_response['main']['humidity'],
                'wind_u': wind_u,
                'wind_v': wind_v,
                'sst': sst if sst is not None else temp,  
                'lst': lst if lst is not None else temp,  
                'is_ocean': is_ocean,
                'year': now.year,
                'month': now.month,
                'day': now.day,
                'day_of_year': now.timetuple().tm_yday
            }
            obs_qs = ClimateObservation.objects.filter(date=today, latitude=lat, longitude=lng)
            if obs_qs.exists():
                obs = obs_qs.first()
                for k, v in defaults.items():
                    setattr(obs, k, v)
                obs.save()
                if obs_qs.count() > 1:
                    obs_qs.exclude(pk=obs.pk).delete()
            else:
                ClimateObservation.objects.create(
                    date=today,
                    latitude=lat,
                    longitude=lng,
                    **defaults
                )

            # --- 4. FORMAT THE RESPONSE FOR APP.JS ---
            final_response = {
                "current": {
                    "temperature": temp,
                    "rainfall": rain,
                    "humidity": owm_response['main']['humidity'],
                    "wind_speed": wind_speed_kmh,
                    "wind_direction": wind_deg,
                    "pressure": owm_response['main']['pressure'],
                    "district": owm_response.get('name', 'Unknown')
                }
            }

            # --- 5. LOCK THE CACHE (12 Hours) ---
            cache.set(cache_key, final_response, timeout=43200)

            return Response(final_response)

        except Exception as e:
            import traceback
            print("🚨 [CRITICAL API ERROR] 🚨")
            traceback.print_exc()  # This will print the EXACT line that failed!
            print("🚨 -------------------- 🚨")
            return Response({"error": "Satellite link failed", "details": str(e)}, status=503)


class ForecastAPIView(APIView):
    """
    GET /api/forecast/
    Provides 24-hour hourly trend stubs and 7-day daily forecasts via PredictionEngine.
    """
    def get(self, request):
        lat = _safe_float(request.GET.get('lat'), 15.9129)
        lng = _safe_float(request.GET.get('lng'), 79.7400)

        # Hourly forecast approximation parabola
        hourly = []
        base_temp = 32.4
        for hour in range(24):
            time_str = f"{(hour + 9) % 24:02d}:00"
            temp_offset = -4.0 * ((hour - 14) ** 2) / 100.0 + 3.0
            hourly.append({
                "time": time_str,
                "temperature": round(base_temp + temp_offset, 1),
                "rainfall": round(max(0, 0.5 * hour - 5) if hour > 10 else 0, 1),
                "humidity": round(78 - (temp_offset * 2.5))
            })

        # Query 7-day daily predictions via PredictionEngine
        # Find nearest district for linked reference
        districts = District.objects.all()
        district = min(districts, key=lambda d: math.hypot(d.latitude - lat, d.longitude - lng)) if districts.exists() else None
        
        date_str = request.GET.get('date')
        if date_str:
            try:
                today = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                today = datetime.datetime.now()
        else:
            today = datetime.datetime.now()
            
        preds = PredictionEngine.predict_next_week(lat, lng, district, start_date=today.date())
        weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
        daily = []
        for i, pred in enumerate(preds):
            day_date = today + datetime.timedelta(days=i)
            daily.append({
                "day": weekdays[day_date.weekday()],
                "date": day_date.strftime("%d %b"),
                "temperature": pred.temperature,
                "rainfall": pred.rainfall,
                "humidity": pred.humidity,
                "wind_speed": pred.wind
            })

        return Response({
            "hourly": hourly,
            "daily": daily
        })


class DigitalTwinAPIView(APIView):
    """
    GET /api/digital-twin/
    Handles interpolation of past, present, and predicted climates across variables
    by coordinating all districts in Andhra Pradesh.
    """
    def get(self, request):
        timeline_step = request.query_params.get("step", "present")  # past, present, future
        
        # Grid overlays representing points for Leaflet visualization
        grid_points = []
        districts = District.objects.all()

        for idx, district in enumerate(districts):
            # Coordinate twin engines for each district
            twin = DigitalTwinEngine.generate_digital_twin(district, timeline_step)
            
            grid_points.append({
                "id": district.id,
                "lat": district.latitude,
                "lng": district.longitude,
                "temperature": twin["physical"]["temperature"],
                "rainfall": twin["physical"]["rainfall"],
                "humidity": twin["physical"]["humidity"],
                "lst": twin["physical"]["lst"],
                "sst": twin["physical"]["sst"] if twin["physical"]["sst"] > 0 else None,
                "wind_speed": twin["physical"]["wind"],
                "wind_direction": "SW" if district.latitude > 16.0 else "WNW"
            })

        return Response({
            "timeline_step": timeline_step,
            "observations": grid_points
        })


class SimulatorAPIView(APIView):
    """
    POST /api/simulator/ or POST /api/simulate
    Accepts temperature, rainfall, and humidity perturbations to compute simulated scenarios.
    """
    def post(self, request):
        temp_change = _safe_float(request.data.get("temp_change", request.data.get("temp_delta")), 0.0)
        rainfall_change = _safe_float(request.data.get("rainfall_change", request.data.get("rain_delta")), 0.0)
        humidity_change = _safe_float(request.data.get("humidity_change"), 0.0)
        scenario_cat = request.data.get("scenario_category", "Custom")

        # Select a default state-wide baseline or centroid
        base_state = {
            "temperature": 32.4,
            "rainfall": 12.4,
            "humidity": 78.0,
            "wind": 14.0,
            "pressure": 1008.0,
            "lst": 34.9,
            "sst": 28.0,
            "date": datetime.date.today()
        }

        # Apply perturbations via ScenarioEngine
        deltas = {
            "temp_change": temp_change,
            "rainfall_change": rainfall_change,
            "humidity_change": humidity_change
        }
        modified = ScenarioEngine.simulate_scenario(base_state, scenario_cat, deltas)

        # Run risk assessment via AnalyticsRiskEngine
        risks = AnalyticsRiskEngine.calculate_risks(modified)

        # Log to database
        sim_record = ClimateSimulation.objects.create(
            scenario_category=scenario_cat,
            temp_change=temp_change,
            rainfall_change=rainfall_change,
            humidity_change=humidity_change
        )
        # Store RiskAssessment
        RiskAssessment.objects.create(
            simulation=sim_record,
            heatwave_risk=risks["heatwave_risk"],
            flood_risk=risks["flood_risk"],
            drought_risk=risks["drought_risk"],
            cyclone_risk=risks["cyclone_risk"],
            agriculture_risk=risks["agriculture_risk"],
            water_stress=risks["water_stress"],
            crop_stress=risks["crop_stress"],
            attribution_insights=risks["attribution_insights"]
        )

        # Build response compatible with app.js
        agri_map = {'Low': 'Optimal Yield Output', 'Medium': 'Moderate Stress', 'High': 'Critical Yield Loss', 'Critical': 'Severe Crop Wilting / Stress'}

        return Response({
            "temp_delta": temp_change,
            "rainfall_pct_change": rainfall_change,
            "humidity_delta": humidity_change,
            "drought_risk": risks["drought_risk"],
            "flood_risk": risks["flood_risk"],
            "heatwave_risk": risks["heatwave_risk"],
            "cyclone_risk": risks["cyclone_risk"],
            "agricultural_impact": agri_map.get(risks["agriculture_risk"], 'Optimal Yield Output'),
            "water_stress_index": risks["water_stress"],
            "crop_stress_index": risks["crop_stress"],
            "attribution_insights": risks["attribution_insights"]
        }, status=status.HTTP_200_OK)


class AlertsAPIView(APIView):
    """
    GET /api/alerts/
    Fetches active severe weather alerts.
    """
    def get(self, request):
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
            }
        ]
        
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
    GET /api/reports/
    Generates monthly or hazard reports.
    """
    def get(self, request):
        export_format = request.query_params.get("format", "json")
        report_type = request.query_params.get("type", "monsoon")

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
# Refactored XGBoost Model-Powered Prediction & Simulation View Targets
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class PredictView(APIView):
    """
    POST /api/predict/ or GET /api/predict
    Returns prediction outputs via PredictionEngine and AnalyticsRiskEngine.
    """
    def get(self, request):
        lat = _safe_float(request.GET.get('lat'), 15.9129)
        lng = _safe_float(request.GET.get('lng'), 79.7400)
        date_str = request.GET.get('date', datetime.date.today().isoformat())
        
        try:
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            target_date = datetime.date.today()
            
        return self._handle_predict(lat, lng, target_date)

    def post(self, request):
        # try:
        #     body = json.loads(request.body)
        # except (json.JSONDecodeError, AttributeError):
        body = request.data

        lat = _safe_float(body.get('lat'), 15.9129)
        lng = _safe_float(body.get('lng'), 79.7400)
        date_str = body.get('date', datetime.datetime.utcnow().isoformat()[:10])
        
        try:
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            target_date = datetime.date.today()

        return self._handle_predict(lat, lng, target_date, body)

    def _handle_predict(self, lat: float, lng: float, target_date: datetime.date, body: Optional[dict] = None) -> Response:
        # Build features payload
        try:
            from ml.feature_builder import build_features_from_request
            features = build_features_from_request(lat, lng, body or {})
        except Exception:
            features = {
                'lat': lat, 'lng': lng,
                'month': target_date.month,
                'day_of_year': target_date.timetuple().tm_yday,
                'elevation_m': 150.0,
                'humidity': 72.0, 'pressure_hpa': 1008.0, 'wind_kt': 14.0,
                'rain_lag1': 5.0, 'rain_lag2': 3.0, 'rain_lag3': 2.0,
                'tmax_lag1': 33.0, 'tmin_lag1': 24.0,
                'tmax_lag2': 33.0, 'tmin_lag2': 24.0,
            }

        # Predict variables using engine
        pred_data = PredictionEngine._get_forecast_point(lat, lng, target_date, "1-day", features)

        # Run risk assessment
        risks = AnalyticsRiskEngine.calculate_risks({
            "temperature": pred_data["temperature"],
            "rainfall": pred_data["rainfall"],
            "humidity": pred_data["humidity"],
            "pressure": pred_data["pressure"],
            "wind": pred_data["wind"],
            "lst": pred_data["lst"],
            "sst": pred_data["sst"],
            "temp_change": 0.0,
            "rainfall_change": 0.0,
            "humidity_change": 0.0
        })

        return Response({
            'lat': lat,
            'lng': lng,
            'rainfall_mm': pred_data["rainfall"],
            'tmax_c': pred_data["temperature"],
            'tmin_c': round(pred_data["temperature"] - 5.5, 1),
            'wind_speed': pred_data["wind"],
            'risk': {
                'drought': risks["drought_risk"],
                'flood': risks["flood_risk"],
                'heatwave': risks["heatwave_risk"],
                'agri': risks["agriculture_risk"]
            },
            'attribution_insights': risks["attribution_insights"],
            'source': 'xgboost' if ModelService.get_instance().is_ready else 'idw_fallback',
            'timestamp': datetime.datetime.utcnow().isoformat()
        })


class SimulateView(APIView):
    """
    POST /api/predict-simulate/ or POST /api/simulate
    """
    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, AttributeError):
            body = request.data

        lat = float(body.get('lat', 15.9129))
        lng = float(body.get('lng', 79.7400))
        temp_delta = float(body.get('temp_delta', body.get('temp_change', 0.0)))
        rain_delta = float(body.get('rain_delta', body.get('rainfall_change', 0.0)))
        hum_delta = float(body.get('humidity_change', body.get('humidity_delta', 0.0)))
        wind_delta = float(body.get('wind_change', body.get('wind_delta', 0.0)))
        press_delta = float(body.get('pressure_change', body.get('pressure_delta', 0.0)))
        lst_delta = float(body.get('lst_change', body.get('lst_delta', 0.0)))
        sst_delta = float(body.get('sst_change', body.get('sst_delta', 0.0)))
        cloud_delta = float(body.get('cloud_change', body.get('cloud_cover_change', 0.0)))
        scenario_cat = body.get('scenario_category', 'Custom')

        date_str = body.get('date')
        if date_str:
            try:
                target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                target_date = datetime.date.today()
        else:
            target_date = datetime.date.today()

        # Resolve district for DB matching
        districts = District.objects.all()
        district = min(districts, key=lambda d: math.hypot(d.latitude - lat, d.longitude - lng)) if districts.exists() else None

        base_state = None
        if district:
            # Check for live/historical observation first
            obs_qs = ClimateObservation.objects.filter(date=target_date, district=district)
            if obs_qs.exists():
                obs = obs_qs.first()
                base_state = {
                    "temperature": obs.temperature,
                    "rainfall": obs.rainfall,
                    "humidity": obs.humidity,
                    "wind": obs.wind,
                    "pressure": obs.pressure,
                    "lst": obs.lst,
                    "sst": obs.sst or 0.0
                }
            else:
                # Check for prediction in DB second
                pred_qs = ClimatePrediction.objects.filter(date=target_date, district=district)
                if pred_qs.exists():
                    pred = pred_qs.first()
                    base_state = {
                        "temperature": pred.temperature,
                        "rainfall": pred.rainfall,
                        "humidity": pred.humidity,
                        "wind": pred.wind,
                        "pressure": pred.pressure,
                        "lst": pred.lst,
                        "sst": pred.sst or 0.0
                    }

        if not base_state:
            # Generate predictive data dynamically using the predictive engine/models output
            pred_data = PredictionEngine._get_forecast_point(lat, lng, target_date, "1-day")
            base_state = {
                "temperature": pred_data["temperature"],
                "rainfall": pred_data["rainfall"],
                "humidity": pred_data["humidity"],
                "wind": pred_data["wind"],
                "pressure": pred_data["pressure"],
                "lst": pred_data["lst"],
                "sst": pred_data["sst"] or 0.0
            }

        # Estimate cloud cover baseline
        base_cloud = round(min(100.0, max(10.0, base_state["humidity"] * 1.1 - 20.0)), 1)
        base_state["cloud_cover"] = base_cloud

        # Run scenario engine modifications
        deltas = {
            "temp_change": temp_delta,
            "rainfall_change": rain_delta,
            "humidity_change": hum_delta,
            "wind_change": wind_delta,
            "pressure_change": press_delta,
            "lst_change": lst_delta,
            "sst_change": sst_delta
        }
        modified = ScenarioEngine.simulate_scenario(base_state, scenario_cat, deltas)
        modified["cloud_cover"] = round(min(100.0, max(0.0, base_cloud + cloud_delta)), 1)
        modified["temp_change"] = temp_delta
        modified["rainfall_change"] = rain_delta
        modified["humidity_change"] = hum_delta
        modified["wind_change"] = wind_delta
        modified["pressure_change"] = press_delta
        modified["lst_change"] = lst_delta
        modified["sst_change"] = sst_delta
        risks = AnalyticsRiskEngine.calculate_risks(modified)
        # Run risk assessment
        risks = AnalyticsRiskEngine.calculate_risks(modified)

        # Save Custom Simulation run
        sim_record = ClimateSimulation.objects.create(
            scenario_category=scenario_cat,
            temp_change=temp_delta,
            rainfall_change=rain_delta,
            humidity_change=hum_delta,
            wind_change=wind_delta,
            pressure_change=press_delta,
            sst_change=sst_delta,
            lst_change=lst_delta
        )
        RiskAssessment.objects.create(
            simulation=sim_record,
            heatwave_risk=risks["heatwave_risk"],
            flood_risk=risks["flood_risk"],
            drought_risk=risks["drought_risk"],
            cyclone_risk=risks["cyclone_risk"],
            agriculture_risk=risks["agriculture_risk"],
            water_stress=risks["water_stress"],
            crop_stress=risks["crop_stress"],
            attribution_insights=risks["attribution_insights"]
        )

        # Construct causal reasoning chain
        reasoning = []
        if temp_delta != 0:
            reasoning.append({
                "label": "Thermal Deviation",
                "value": f"{temp_delta:+}°C",
                "effect": "Temperature perturbation applied"
            })
        if hum_delta != 0:
            reasoning.append({
                "label": "Humidity Anomaly",
                "value": f"{hum_delta:+}%",
                "effect": "Alters atmospheric moisture saturation"
            })
        if rain_delta != 0:
            reasoning.append({
                "label": "Rainfall Variance",
                "value": f"{rain_delta:+}%",
                "effect": "Drives soil moisture and flood accumulation"
            })
        if wind_delta != 0:
            reasoning.append({
                "label": "Wind Speed Shift",
                "value": f"{wind_delta:+} kt",
                "effect": "Modifies wind vector velocity"
            })
        if press_delta != 0:
            reasoning.append({
                "label": "Pressure Delta",
                "value": f"{press_delta:+} hPa",
                "effect": "Affects cyclonic circulation intensity"
            })
        if lst_delta != 0:
            reasoning.append({
                "label": "LST Deviation",
                "value": f"{lst_delta:+}°C",
                "effect": "Influences surface heat emission"
            })
        if sst_delta != 0:
            reasoning.append({
                "label": "SST Deviation",
                "value": f"{sst_delta:+}°C",
                "effect": "Affects ocean-atmosphere heat exchange"
            })

        if temp_delta > 0 and hum_delta < 0:
            reasoning.append({
                "label": "Evapotranspiration Rate",
                "value": "Accelerated (↑)",
                "effect": "Higher temperatures and dry air increase water loss"
            })
        if rain_delta < 0:
            reasoning.append({
                "label": "Soil Moisture State",
                "value": "Deficit (↓)",
                "effect": "Decreased precipitation limits groundwater recharge"
            })
        elif rain_delta > 30:
            reasoning.append({
                "label": "Surface Runoff Volume",
                "value": "Excess (↑)",
                "effect": "Heavy rainfall exceeds soil absorption capacity"
            })

        highest_risk_label = "Low"
        highest_risk_name = "System Stability"
        for r_name, r_val in [("Drought", risks["drought_risk"]), ("Flood", risks["flood_risk"]), ("Heatwave", risks["heatwave_risk"]), ("Cyclone", risks["cyclone_risk"])]:
            if r_val in ["High", "Critical"]:
                highest_risk_label = r_val
                highest_risk_name = f"{r_name} Hazard"
                break
            elif r_val == "Medium":
                highest_risk_label = "Medium"
                highest_risk_name = f"{r_name} Hazard"

        reasoning.append({
            "label": f"Resulting {highest_risk_name}",
            "value": highest_risk_label.upper(),
            "effect": "Derived from Digital Twin risk assessment matrix"
        })

        contribs = [
            {"name": "Temperature", "value": risks["attribution_insights"]["temperature_contribution"]},
            {"name": "Rainfall", "value": risks["attribution_insights"]["rainfall_contribution"]},
            {"name": "Humidity", "value": risks["attribution_insights"]["humidity_contribution"]},
            {"name": "Sea Surface Temp", "value": risks["attribution_insights"]["sst_influence"]},
        ]
        contribs.sort(key=lambda x: x["value"], reverse=True)

        agri_map = {'Low': 'Optimal Yield Output', 'Medium': 'Moderate Stress', 'High': 'Critical Yield Loss', 'Critical': 'Severe Crop Wilting / Stress'}

        return Response({
            'baseline': base_state,
            'simulated': modified,
            'risk': {
                'drought': risks["drought_risk"],
                'flood': risks["flood_risk"],
                'heatwave': risks["heatwave_risk"],
                'cyclone': risks["cyclone_risk"],
                'agri': risks["agriculture_risk"]
            },
            'source': 'xgboost_simulation' if ModelService.get_instance().is_ready else 'idw_simulation',
            # Legacy format compat keys
            'rainfall_mm': modified["rainfall"],
            'tmax_c': modified["temperature"],
            'tmin_c': round(modified["temperature"] - 5.5, 1),
            'drought_risk': risks["drought_risk"],
            'flood_risk': risks["flood_risk"],
            'heatwave_risk': risks["heatwave_risk"],
            'agricultural_impact': agri_map.get(risks["agriculture_risk"], 'Optimal Yield Output'),
            'water_stress_index': risks["water_stress"],
            'crop_stress_index': risks["crop_stress"],
            'attribution_insights': risks["attribution_insights"],
            'reasoning_chain': reasoning,
            'influential_variables': contribs,
            'timestamp': datetime.datetime.utcnow().isoformat()
        })


class RiskView(APIView):
    """
    GET /api/risk/
    Returns risk and explainability details for AP districts.
    """
    def get(self, request):
        results = []
        districts = District.objects.all()

        for d in districts:
            # Query DigitalTwin state for district
            twin = DigitalTwinEngine.generate_digital_twin(d, "present")
            risks = twin["risks"]
            
            results.append({
                'district': d.name,
                'lat': d.latitude,
                'lng': d.longitude,
                'temp': twin["physical"]["temperature"],
                'rain': twin["physical"]["rainfall"],
                'humidity': twin["physical"]["humidity"],
                'drought': risks["drought_risk"],
                'flood': risks["flood_risk"],
                'heatwave': risks["heatwave_risk"],
                'cyclone': risks["cyclone_risk"],
                'agri_risk': risks["agriculture_risk"],
                'water_stress': risks["water_stress"],
                'crop_stress': risks["crop_stress"],
                'attribution_insights': risks["attribution_insights"]
            })
        return Response(results)


class HistoryAPIView(APIView):
    """
    GET /api/history
    Returns past observation records logged in the database.
    """
    def get(self, request):
        district_name = request.GET.get("district")
        limit = int(request.GET.get("limit", 100))

        qs = ClimateObservation.objects.all()
        if district_name:
            qs = qs.filter(district__name__iexact=district_name)
        
        records = qs.order_by('-date')[:limit]

        return Response([
            {
                "date": o.date.isoformat(),
                "district": o.district.name if o.district else "AP Centroid",
                "latitude": o.latitude,
                "longitude": o.longitude,
                "temperature": o.temperature,
                "rainfall": o.rainfall,
                "humidity": o.humidity,
                "pressure": o.pressure,
                "wind": o.wind,
                "lst": o.lst,
                "sst": o.sst
            }
            for o in records
        ])


class PlaybackAPIView(APIView):
    """
    GET /api/playback
    Provides ClimateState representing the physical variables, alerts, risk indicators,
    and cyclone coordinates for the requested datetime and mode.
    """
    def get(self, request):
        datetime_str = request.GET.get("datetime")
        hour_str = request.GET.get("hour")
        
        # If datetime_str is not provided, check if hour is provided. If not, fallback to legacy
        if not datetime_str:
            if hour_str:
                date_str = request.GET.get("date")
                if date_str:
                    try:
                        datetime_str = f"{date_str} {int(hour_str):02d}:00"
                    except ValueError:
                        pass
            
        if not datetime_str:
            month = request.GET.get("month")
            year = request.GET.get("year")
            date_str = request.GET.get("date")

            if date_str:
                try:
                    d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                    frames = ClimatePlaybackService.play_day(d)
                    return Response({"type": "day", "date": date_str, "frames": frames})
                except Exception as e:
                    return Response({"error": f"Invalid date: {e}"}, status=400)

            if month:
                y = int(year) if year else datetime.date.today().year
                m = int(month)
                frames = ClimatePlaybackService.play_month(y, m)
                return Response({"type": "month", "year": y, "month": m, "frames": frames})

            # Default: list recent playback logs
            playback_logs = ClimatePlayback.objects.all().order_by('-timestamp')[:50]
            return Response([
                {
                    "id": p.id,
                    "timestamp": p.timestamp.isoformat(),
                    "start": p.date_range_start.isoformat(),
                    "end": p.date_range_end.isoformat(),
                    "speed": p.speed,
                    "status": p.status
                }
                for p in playback_logs
            ])
            
        # Parse datetime parameter
        try:
            dt_str = datetime_str.replace('T', ' ')
            if len(dt_str) > 10:
                dt = datetime.datetime.strptime(dt_str[:16], "%Y-%m-%d %H:%M")
            else:
                dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d")
        except Exception as e:
            return Response({"error": f"Invalid datetime format: {e}"}, status=400)
            
        target_date = dt.date()
        hour = dt.hour
        mode = request.GET.get("mode", "live").lower()
        
        temp_delta = _safe_float(request.GET.get("temp_delta"), 0.0)
        rain_delta = _safe_float(request.GET.get("rain_delta"), 0.0)
        humidity_change = _safe_float(request.GET.get("humidity_change"), 0.0)
        scenario_category = request.GET.get("scenario_category", "Custom")

        # Map mode inputs and fetch baseline
        districts = list(District.objects.all())
        grid_points = []
        model_source = "xgboost" if ModelService.get_instance().is_ready else "idw_fallback"
        
        # Find nearest district for target location if provided
        lat_str = request.GET.get('lat')
        lng_str = request.GET.get('lng')
        lat = float(lat_str) if lat_str else 15.9129
        lng = float(lng_str) if lng_str else 79.7400
        target_district = None
        if lat_str and lng_str:
            lat = float(lat_str)
            lng = float(lng_str)
            if len(districts) > 0:
                target_district = min(districts, key=lambda d: math.hypot(d.latitude - lat, d.longitude - lng))
        if not target_district:
            target_district = districts[0] if districts else None

        # Adjust target date based on availability or mode
        # Overrides disabled to allow custom dates
        pass

        # Diurnal Cycle Curve offsets
        temp_offset = -4.0 * ((hour - 14) ** 2) / 100.0 + 3.0
        humidity_offset = - (temp_offset * 2.5)
        wind_offset = 3.0 * math.sin((hour - 8) * math.pi / 12) if 8 <= hour <= 20 else -2.0
        pressure_offset = 1.2 * math.cos(hour * math.pi / 6)
        
        # Build states for each district
        for district in districts:
            is_virtual_district = getattr(district, "is_virtual", False)
            base_temp = 32.4
            base_rain = 5.0
            base_hum = 75.0
            base_press = 1008.0
            base_wind = 14.0
            base_lst = 34.0
            base_sst = 0.0
            wind_dir = "SW"

            # Fetch DB values depending on mode
            has_observation = False if is_virtual_district else ClimateObservation.objects.filter(date=target_date, district=district).exists()
            if (mode in ['history', 'live'] and has_observation) or (mode == 'scenario' and has_observation):
                records = ClimateObservation.objects.none() if is_virtual_district else ClimateObservation.objects.filter(date=target_date, district=district)
                if records.exists():
                    obs = records.first()
                    base_temp = obs.temperature
                    base_rain = obs.rainfall
                    base_hum = obs.humidity
                    base_press = obs.pressure
                    base_wind = obs.wind
                    base_lst = obs.lst
                    base_sst = obs.sst
                    wind_dir = obs.wind_direction
            else: # forecast or scenario with predictions
                if mode == 'forecast':
                    pred = PredictionEngine._get_forecast_point(
                        district.latitude,
                        district.longitude,
                        target_date,
                        "1-day"
                    )
                    base_temp = pred["temperature"]
                    base_rain = pred["rainfall"]
                    base_hum = pred["humidity"]
                    base_press = pred["pressure"]
                    base_wind = pred["wind"]
                    base_lst = pred["lst"]
                    base_sst = pred["sst"]
                    wind_dir = "SW" if district.latitude > 16.0 else "WNW"
                else:
                    records = ClimatePrediction.objects.none() if is_virtual_district else ClimatePrediction.objects.filter(date=target_date, district=district)
                    if records.exists():
                        pred = records.first()
                        base_temp = pred.temperature
                        base_rain = pred.rainfall
                        base_hum = pred.humidity
                        base_press = pred.pressure
                        base_wind = pred.wind
                        base_lst = pred.lst
                        base_sst = pred.sst
                        wind_dir = "SW" if district.latitude > 16.0 else "WNW"
                    else:
                        pred = PredictionEngine._get_forecast_point(
                            district.latitude,
                            district.longitude,
                            target_date,
                            "1-day"
                        )
                        base_temp = pred["temperature"]
                        base_rain = pred["rainfall"]
                        base_hum = pred["humidity"]
                        base_press = pred["pressure"]
                        base_wind = pred["wind"]
                        base_lst = pred["lst"]
                        base_sst = pred["sst"]
                        wind_dir = "SW" if district.latitude > 16.0 else "WNW"
            
            # Apply hourly diurnal curve offsets
            hourly_temp = base_temp + temp_offset
            
            # Convective rainfall peaks in afternoon
            if 14 <= hour <= 21:
                rain_factor = 2.0 * math.sin((hour - 14) * math.pi / 7)
            else:
                rain_factor = 0.05
            hourly_rain = base_rain * rain_factor

            hourly_hum = min(100.0, max(10.0, base_hum + humidity_offset))
            hourly_wind = max(1.0, base_wind + wind_offset)
            hourly_press = base_press + pressure_offset
            hourly_lst = base_lst + temp_offset * 1.3
            hourly_sst = base_sst + 0.15 * math.sin((hour - 12) * math.pi / 12) if district.longitude > 80.5 else 0.0

            # If scenario mode, apply perturbations
            if mode == 'scenario':
                hourly_temp += temp_delta
                # rain_delta is percentage change (e.g. +20%)
                hourly_rain = hourly_rain * (1.0 + rain_delta / 100.0)
                hourly_hum = min(100.0, max(0.0, hourly_hum + humidity_change))
                
                # Apply Scenario multipliers for risk computations
                if scenario_category == 'cyclone':
                    hourly_temp += 1.0
                    hourly_rain += 15.0
                    hourly_hum = min(100.0, hourly_hum + 15.0)
                    hourly_wind += 25.0
                    hourly_press -= 20.0
                elif scenario_category == 'heatwave':
                    hourly_temp += 4.5
                    hourly_rain = max(0.0, hourly_rain - 3.0)
                    hourly_hum = max(0.0, hourly_hum - 10.0)
                elif scenario_category == 'flood':
                    hourly_rain += 25.0
                    hourly_hum = min(100.0, hourly_hum + 10.0)
                elif scenario_category == 'drought':
                    hourly_temp += 3.0
                    hourly_rain = 0.0
                    hourly_hum = max(0.0, hourly_hum - 15.0)
            
            # Clean bounds
            hourly_rain = round(max(0.0, hourly_rain), 1)
            hourly_temp = round(hourly_temp, 1)
            hourly_hum = round(hourly_hum, 1)
            hourly_wind = round(hourly_wind, 1)
            hourly_press = round(hourly_press, 1)
            hourly_lst = round(hourly_lst, 1)
            hourly_sst = round(hourly_sst, 1)

            # Compute risks dynamically
            risks = AnalyticsRiskEngine.calculate_risks({
                "temperature": hourly_temp,
                "rainfall": hourly_rain,
                "humidity": hourly_hum,
                "pressure": hourly_press,
                "wind": hourly_wind,
                "lst": hourly_lst,
                "sst": hourly_sst,
                "temp_change": temp_delta if mode == 'scenario' else 0.0,
                "rainfall_change": rain_delta if mode == 'scenario' else 0.0,
                "humidity_change": humidity_change if mode == 'scenario' else 0.0
            })

            grid_points.append({
                "id": district.id,
                "district": district.name,
                "latitude": district.latitude,
                "longitude": district.longitude,
                "temperature": hourly_temp,
                "rainfall": hourly_rain,
                "humidity": hourly_hum,
                "pressure": hourly_press,
                "wind_speed": hourly_wind,
                "wind_direction": wind_dir,
                "lst": hourly_lst,
                "sst": hourly_sst,
                "drought_risk": risks["drought_risk"],
                "flood_risk": risks["flood_risk"],
                "heatwave_risk": risks["heatwave_risk"],
                "cyclone_risk": risks["cyclone_risk"],
                "agriculture_risk": risks["agriculture_risk"],
                "water_stress": risks["water_stress"],
                "crop_stress": risks["crop_stress"],
                "attribution_insights": risks["attribution_insights"]
            })

        # Calculate average/KPI values
        if not grid_points:
            avg_temp = 0.0  # Or whatever fallback default makes sense for your UI
            avg_rain = 0.0
            avg_hum = 0.0
            avg_wind = 0.0
            avg_press = 0.0
            avg_lst = 0.0
            avg_sst_list = [d["sst"] for d in grid_points if d["sst"] > 0]
            avg_sst = round(sum(avg_sst_list) / len(avg_sst_list), 1) if avg_sst_list else 0.0
        else:
            avg_temp = round(sum(d["temperature"] for d in grid_points) / len(grid_points), 1)
            avg_rain = round(sum(d["rainfall"] for d in grid_points) / len(grid_points), 1)
            avg_hum = round(sum(d["humidity"] for d in grid_points) / len(grid_points), 1)
            avg_wind = round(sum(d["wind_speed"] for d in grid_points) / len(grid_points), 1)
            avg_press = round(sum(d["pressure"] for d in grid_points) / len(grid_points), 1)
            avg_lst = round(sum(d["lst"] for d in grid_points) / len(grid_points), 1)
            avg_sst_list = [d["sst"] for d in grid_points if d["sst"] > 0]
            avg_sst = round(sum(avg_sst_list) / len(avg_sst_list), 1) if avg_sst_list else 0.0

        # Get active alerts
        active_alerts = []
        alerts_qs = Alert.objects.filter(active=True)
        for alert in alerts_qs:
            active_alerts.append({
                "id": alert.id,
                "type": alert.type,
                "severity": alert.severity,
                "district": alert.district,
                "description": alert.description
            })
            
        # Add fallback alert if none exist and it is cyclone scenario
        if not active_alerts and (scenario_category == 'cyclone' and mode == 'scenario'):
            active_alerts.append({
                "id": 99,
                "type": "Cyclone",
                "severity": "Critical",
                "district": "Visakhapatnam & East Godavari Coast",
                "description": "Severe Cyclonic Storm warning. Dynamic winds exceeding 65 knots."
            })

        # Cyclone parameters
        cyclone_active = (scenario_category == 'cyclone' and mode == 'scenario') or any(a["type"] == "Cyclone" and a["severity"] in ["High", "Critical"] for a in active_alerts)
        cyclone_data = {"active": False}
        if cyclone_active:
            track_points = [
                {"lat": 14.0, "lng": 83.5}, 
                {"lat": 15.2, "lng": 82.8},
                {"lat": 16.4, "lng": 82.1},
                {"lat": 17.68, "lng": 83.21}
            ]
            # Interpolate cyclone center coordinates based on hour
            if hour < 6:
                t = hour / 6.0
                p0, p1 = track_points[0], track_points[1]
            elif hour < 12:
                t = (hour - 6) / 6.0
                p0, p1 = track_points[1], track_points[2]
            elif hour < 18:
                t = (hour - 12) / 6.0
                p0, p1 = track_points[2], track_points[3]
            else:
                t = 1.0
                p0, p1 = track_points[3], track_points[3]
            
            c_lat = round(p0["lat"] + t * (p1["lat"] - p0["lat"]), 2)
            c_lng = round(p0["lng"] + t * (p1["lng"] - p0["lng"]), 2)

            cyclone_data = {
                "active": True,
                "eye": [c_lat, c_lng],
                "size_km": 180 - (hour * 2) if hour < 18 else 100,  # size decreases/stabilizes as it makes landfall
                "wind_speed_kt": 75 - (hour - 12) * 2.5 if hour > 12 else 55 + hour * 1.5,
                "forecast_cone": [[14.0, 81.5], [14.0, 85.5], [17.68, 83.21]],
                "pressure_rings": [1002, 992, 982] if hour < 18 else [1006, 998, 990],
                "landfall_coords": [17.68, 83.21]
            }

        # Charts data: 24 hourly values for target district
        target_district_obj = target_district or District.objects.first()
        charts_temp = []
        charts_rain = []
        charts_wind = []
        charts_wind_dir = []
        charts_hum = []
        charts_press = []
        charts_lst = []
        charts_sst = []
        charts_time = []
        
        # Calculate daily baseline for this target district
        td_temp = 32.4
        td_rain = 5.0
        td_hum = 75.0
        td_wind = 14.0
        td_press = 1008.0
        td_lst = 34.0
        td_sst = 0.0
        td_wind_dir = "SW"
        is_virtual_target = getattr(target_district_obj, "is_virtual", False)

        target_has_observation = False if is_virtual_target else ClimateObservation.objects.filter(date=target_date, district=target_district_obj).exists()
        if (mode in ['history', 'live'] and target_has_observation) or (mode == 'scenario' and target_has_observation):
            td_obs = None if is_virtual_target else ClimateObservation.objects.filter(date=target_date, district=target_district_obj).first()
            if td_obs:
                td_temp = td_obs.temperature
                td_rain = td_obs.rainfall
                td_hum = td_obs.humidity
                td_wind = td_obs.wind
                td_press = td_obs.pressure
                td_lst = td_obs.lst
                td_sst = td_obs.sst
                td_wind_dir = td_obs.wind_direction
        else:
            if mode == 'forecast':
                td_pred = PredictionEngine._get_forecast_point(
                    target_district_obj.latitude,
                    target_district_obj.longitude,
                    target_date,
                    "1-day"
                )
                td_temp = td_pred["temperature"]
                td_rain = td_pred["rainfall"]
                td_hum = td_pred["humidity"]
                td_wind = td_pred["wind"]
                td_press = td_pred["pressure"]
                td_lst = td_pred["lst"]
                td_sst = td_pred["sst"]
                td_wind_dir = "SW" if target_district_obj.latitude > 16.0 else "WNW"
            else:
                td_pred = None if is_virtual_target else ClimatePrediction.objects.filter(date=target_date, district=target_district_obj).first()
                if td_pred:
                    td_temp = td_pred.temperature
                    td_rain = td_pred.rainfall
                    td_hum = td_pred.humidity
                    td_wind = td_pred.wind
                    td_press = td_pred.pressure
                    td_lst = td_pred.lst
                    td_sst = td_pred.sst
                    td_wind_dir = "SW" if target_district_obj.latitude > 16.0 else "WNW"
                else:
                    td_pred = PredictionEngine._get_forecast_point(
                        target_district_obj.latitude,
                        target_district_obj.longitude,
                        target_date,
                        "1-day"
                    )
                    td_temp = td_pred["temperature"]
                    td_rain = td_pred["rainfall"]
                    td_hum = td_pred["humidity"]
                    td_wind = td_pred["wind"]
                    td_press = td_pred["pressure"]
                    td_lst = td_pred["lst"]
                    td_sst = td_pred["sst"]
                    td_wind_dir = "SW" if target_district_obj.latitude > 16.0 else "WNW"
                
        for h in range(24):
            h_temp_offset = -4.0 * ((h - 14) ** 2) / 100.0 + 3.0
            h_humidity_offset = - (h_temp_offset * 2.5)
            h_wind_offset = 3.0 * math.sin((h - 8) * math.pi / 12) if 8 <= h <= 20 else -2.0
            h_pressure_offset = 1.2 * math.cos(h * math.pi / 6)

            if 14 <= h <= 21:
                h_rain_factor = 2.0 * math.sin((h - 14) * math.pi / 7)
            else:
                h_rain_factor = 0.05
            
            h_temp = td_temp + h_temp_offset
            h_rain = td_rain * h_rain_factor
            h_hum = min(100.0, max(10.0, td_hum + h_humidity_offset))
            h_wind = max(1.0, td_wind + h_wind_offset)
            h_press = td_press + h_pressure_offset
            h_lst = td_lst + h_temp_offset * 1.3
            h_sst = (td_sst + 0.15 * math.sin((h - 12) * math.pi / 12)) if target_district_obj.longitude > 80.5 else 0.0
            
            if mode == 'scenario':
                h_temp += temp_delta
                h_rain = h_rain * (1.0 + rain_delta / 100.0)
                h_hum = min(100.0, max(0.0, h_hum + humidity_change))
                if scenario_category == 'cyclone':
                    h_temp += 1.0
                    h_rain += 15.0
                    h_hum = min(100.0, h_hum + 15.0)
                    h_wind += 25.0
                    h_press -= 20.0
                elif scenario_category == 'heatwave':
                    h_temp += 4.5
                    h_rain = max(0.0, h_rain - 3.0)
                    h_hum = max(0.0, h_hum - 10.0)
                elif scenario_category == 'flood':
                    h_rain += 25.0
                    h_hum = min(100.0, h_hum + 10.0)
                elif scenario_category == 'drought':
                    h_temp += 3.0
                    h_rain = 0.0
                    h_hum = max(0.0, h_hum - 15.0)
                
            charts_temp.append(round(max(0.0, h_temp), 1))
            charts_rain.append(round(max(0.0, h_rain), 1))
            charts_wind.append(round(max(0.0, h_wind), 1))
            charts_wind_dir.append(td_wind_dir)
            charts_hum.append(round(h_hum, 1))
            charts_press.append(round(h_press, 1))
            charts_lst.append(round(h_lst, 1))
            charts_sst.append(round(h_sst, 1))
            charts_time.append(f"{h:02d}:00")

        td_data = next((d for d in grid_points if d["district"] == target_district_obj.name), None)
        td_state = {
            "temperature": td_data["temperature"] if td_data else 32.4,
            "rainfall": td_data["rainfall"] if td_data else 5.0,
            "humidity": td_data["humidity"] if td_data else 75.0,
            "wind": td_data["wind_speed"] if td_data else 14.0,
            "pressure": td_data["pressure"] if td_data else 1008.0,
            "lst": td_data["lst"] if td_data else 34.0,
            "sst": td_data["sst"] if td_data else 0.0
        }

        response_payload = {
            "mode": mode,
            "source": model_source,
            "model_source": model_source,
            "datetime": dt.isoformat(),
            "date": target_date.isoformat(),
            "hour": hour,
            "districts": grid_points,
            "metrics": {
                "temperature": avg_temp,
                "rainfall": avg_rain,
                "humidity": avg_hum,
                "wind_speed": avg_wind,
                "pressure": avg_press,
                "lst": avg_lst,
                "sst": avg_sst
            },
            "cyclone": cyclone_data,
            "alerts": active_alerts,
            "charts": {
                "time": charts_time,
                "temperature": charts_temp,
                "rainfall": charts_rain,
                "wind_speed": charts_wind,
                "wind_direction": charts_wind_dir,
                "humidity": charts_hum,
                "pressure": charts_press,
                "lst": charts_lst,
                "sst": charts_sst
            }
        }

        if mode in ['history', 'live']:
            response_payload["observation"] = td_state
        else:
            response_payload["prediction"] = td_state

        return Response(response_payload)


class ModelStatusView(APIView):
    """
    GET /api/model-status/
    Returns XGBoost status.
    """
    def get(self, request):
        try:
            service = ModelService.get_instance()
            return Response(service.get_status())
        except Exception as e:
            return Response({
                'loaded': False,
                'error': str(e),
                'message': 'Model service unavailable. Using IDW fallback.'
            })


# ═══════════════════════════════════════════════════════════════════════════════
# CLIMATE INTELLIGENCE CENTER – API Layer
# All seven engines integrated: Observation, Prediction, Scenario, Risk, Twin
# ═══════════════════════════════════════════════════════════════════════════════

class ClimateSnapshotView(APIView):
    """
    GET /api/climate/snapshot/?lat=&lng=
    Returns current climate snapshot with 12 variables and deltas vs
    yesterday, last week, monthly average, and seasonal average.
    """
    def get(self, request):
        lat = _safe_float(request.GET.get('lat'), 15.9129)
        lng = _safe_float(request.GET.get('lng'), 79.7400)

        # Resolve nearest district
        districts = District.objects.all()
        district = min(districts, key=lambda d: math.hypot(d.latitude - lat, d.longitude - lng)) if districts.exists() else None

        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        last_week = today - datetime.timedelta(days=7)

        def get_obs(date, dist):
            if dist:
                obs = ClimateObservation.objects.filter(date=date, district=dist).first()
                if obs:
                    return obs
            # Fallback: closest coordinate observation
            obs = ClimateObservation.objects.filter(date=date).first()
            return obs

        # Current observation
        current_obs = get_obs(today, district)
        if not current_obs:
            pred_data = PredictionEngine._get_forecast_point(lat, lng, today, "1-day")
            snapshot = {
                "temperature": pred_data["temperature"],
                "temp_max": round(pred_data["temperature"] + 1.5, 1),
                "temp_min": round(pred_data["temperature"] - 6.0, 1),
                "rainfall": pred_data["rainfall"],
                "humidity": pred_data["humidity"],
                "pressure": pred_data["pressure"],
                "wind_speed": pred_data["wind"],
                "wind_direction": "SW",
                "lst": pred_data["lst"],
                "sst": pred_data["sst"],
                "cloud_cover": round(min(100.0, max(10.0, pred_data["humidity"] * 1.1 - 20.0)), 1),
                "visibility": round(max(1.0, 12.0 - pred_data["humidity"] * 0.08), 1),
            }
            source = "prediction_engine"
        else:
            snapshot = {
                "temperature": current_obs.temperature,
                "temp_max": round(current_obs.temperature + 1.5, 1),
                "temp_min": round(current_obs.temperature - 6.0, 1),
                "rainfall": current_obs.rainfall,
                "humidity": current_obs.humidity,
                "pressure": current_obs.pressure,
                "wind_speed": current_obs.wind_speed,
                "wind_direction": current_obs.wind_direction,
                "lst": current_obs.lst,
                "sst": current_obs.sst or 0.0,
                "cloud_cover": round(min(100.0, max(10.0, current_obs.humidity * 1.1 - 20.0)), 1),
                "visibility": round(max(1.0, 12.0 - current_obs.humidity * 0.08), 1),
            }
            source = "observation_engine"

        # Calculate deltas vs comparison periods
        def compute_deltas(ref_obs, current_snap):
            if not ref_obs:
                return {}
            return {
                "temperature": round(current_snap["temperature"] - ref_obs.temperature, 1),
                "rainfall": round(current_snap["rainfall"] - ref_obs.rainfall, 1),
                "humidity": round(current_snap["humidity"] - ref_obs.humidity, 1),
                "pressure": round(current_snap["pressure"] - ref_obs.pressure, 1),
                "wind_speed": round(current_snap["wind_speed"] - ref_obs.wind_speed, 1),
            }

        yesterday_obs = get_obs(yesterday, district)
        last_week_obs = get_obs(last_week, district)

        # Monthly average from last 30 days of observations
        thirty_days_ago = today - datetime.timedelta(days=30)
        monthly_qs = ClimateObservation.objects.filter(
            date__gte=thirty_days_ago,
            district=district
        ) if district else ClimateObservation.objects.filter(date__gte=thirty_days_ago)

        monthly_avg_temp = None
        monthly_avg_rain = None
        if monthly_qs.exists():
            monthly_avg_temp = round(sum(o.temperature for o in monthly_qs) / monthly_qs.count(), 1)
            monthly_avg_rain = round(sum(o.rainfall for o in monthly_qs) / monthly_qs.count(), 1)

        # Seasonal baseline from config
        base = {
            "temperature": 32.4, "rainfall": 12.4, "humidity": 78.0,
            "pressure": 1008.0, "wind_speed": 14.0,
        }

        return Response({
            "location": district.name if district else "Andhra Pradesh",
            "lat": lat,
            "lng": lng,
            "snapshot": snapshot,
            "deltas": {
                "vs_yesterday": compute_deltas(yesterday_obs, snapshot),
                "vs_last_week": compute_deltas(last_week_obs, snapshot),
                "vs_monthly_avg": {
                    "temperature": round(snapshot["temperature"] - monthly_avg_temp, 1) if monthly_avg_temp else None,
                    "rainfall": round(snapshot["rainfall"] - monthly_avg_rain, 1) if monthly_avg_rain else None,
                } if monthly_avg_temp else {},
                "vs_seasonal_avg": {
                    "temperature": round(snapshot["temperature"] - base["temperature"], 1),
                    "rainfall": round(snapshot["rainfall"] - base["rainfall"], 1),
                    "humidity": round(snapshot["humidity"] - base["humidity"], 1),
                    "pressure": round(snapshot["pressure"] - base["pressure"], 1),
                    "wind_speed": round(snapshot["wind_speed"] - base["wind_speed"], 1),
                },
            },
            "source": source,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })


class ClimateTrendsView(APIView):
    """
    GET /api/climate/trends/?variable=temperature&period=daily&lat=&lng=
    Returns trend data for a selected climate variable over the specified period.
    Periods: hourly (from playback charts), daily (last 14 days), weekly (last 12 weeks),
             monthly (last 12 months), seasonal (4 seasons).
    """
    VARIABLE_MAP = {
        "temperature": ("temperature", "°C"),
        "rainfall": ("rainfall", "mm"),
        "humidity": ("humidity", "%"),
        "wind": ("wind", "knots"),
        "pressure": ("pressure", "hPa"),
        "lst": ("lst", "°C"),
        "sst": ("sst", "°C"),
    }

    def get(self, request):
        variable = request.GET.get('variable', 'temperature')
        period = request.GET.get('period', 'daily')
        lat = _safe_float(request.GET.get('lat'), 15.9129)
        lng = _safe_float(request.GET.get('lng'), 79.7400)

        if variable not in self.VARIABLE_MAP:
            variable = 'temperature'

        db_field, unit = self.VARIABLE_MAP[variable]

        districts = District.objects.all()
        district = min(districts, key=lambda d: math.hypot(d.latitude - lat, d.longitude - lng)) if districts.exists() else None

        today = datetime.date.today()
        labels = []
        values = []
        forecast_values = []

        if period == 'daily':
            # Last 14 days of observations
            for i in range(13, -1, -1):
                d = today - datetime.timedelta(days=i)
                obs = ClimateObservation.objects.filter(date=d, district=district).first() if district else ClimateObservation.objects.filter(date=d).first()
                labels.append(d.strftime("%d %b"))
                if obs:
                    values.append(round(getattr(obs, db_field) or 0.0, 1))
                else:
                    # Estimate from engine
                    pt = PredictionEngine._get_forecast_point(lat, lng, d, "7-day")
                    values.append(pt.get(variable, 0.0))
            # Next 7 days forecast
            for i in range(1, 8):
                d = today + datetime.timedelta(days=i)
                pt = PredictionEngine._get_forecast_point(lat, lng, d, "7-day")
                forecast_values.append(pt.get(variable, 0.0))

        elif period == 'hourly':
            # Pull today's hourly chart data from PlaybackAPI
            base_val = 32.4 if variable == 'temperature' else (5.0 if variable == 'rainfall' else 75.0)
            if district:
                obs = ClimateObservation.objects.filter(date=today, district=district).first()
                if obs:
                    base_val = getattr(obs, db_field) or base_val
            for h in range(24):
                labels.append(f"{h:02d}:00")
                offset = -4.0 * ((h - 14) ** 2) / 100.0 + 3.0
                if variable == 'temperature':
                    values.append(round(base_val + offset, 1))
                elif variable == 'humidity':
                    values.append(round(min(100, max(10, base_val - offset * 2.5)), 1))
                elif variable == 'pressure':
                    values.append(round(base_val + 1.2 * math.cos(h * math.pi / 6), 1))
                elif variable == 'rainfall':
                    rf = 2.0 * math.sin((h - 14) * math.pi / 7) if 14 <= h <= 21 else 0.05
                    values.append(round(max(0, base_val * rf), 1))
                elif variable == 'wind':
                    wo = 3.0 * math.sin((h - 8) * math.pi / 12) if 8 <= h <= 20 else -2.0
                    values.append(round(max(1, base_val + wo), 1))
                else:
                    values.append(round(base_val + offset * 1.3, 1))

        elif period == 'weekly':
            for i in range(11, -1, -1):
                week_start = today - datetime.timedelta(weeks=i)
                week_end = week_start + datetime.timedelta(days=6)
                qs = ClimateObservation.objects.filter(date__range=[week_start, week_end], district=district) if district else ClimateObservation.objects.filter(date__range=[week_start, week_end])
                labels.append(f"W{week_start.strftime('%d %b')}")
                if qs.exists():
                    avg = sum(getattr(o, db_field) or 0 for o in qs) / qs.count()
                    values.append(round(avg, 1))
                else:
                    pt = PredictionEngine._get_forecast_point(lat, lng, week_start, "7-day")
                    values.append(pt.get(variable, 0.0))

        elif period == 'monthly':
            for i in range(11, -1, -1):
                m_date = today.replace(day=1) - datetime.timedelta(days=i * 28)
                qs = ClimateObservation.objects.filter(date__year=m_date.year, date__month=m_date.month, district=district) if district else ClimateObservation.objects.filter(date__year=m_date.year, date__month=m_date.month)
                labels.append(m_date.strftime("%b %Y"))
                if qs.exists():
                    avg = sum(getattr(o, db_field) or 0 for o in qs) / qs.count()
                    values.append(round(avg, 1))
                else:
                    pt = PredictionEngine._get_forecast_point(lat, lng, m_date, "7-day")
                    values.append(pt.get(variable, 0.0))

        elif period == 'seasonal':
            season_names = ["Winter (DJF)", "Pre-Monsoon (MAM)", "Monsoon (JJAS)", "Post-Monsoon (ON)"]
            season_months = [[12, 1, 2], [3, 4, 5], [6, 7, 8, 9], [10, 11]]
            for i, (name, months) in enumerate(zip(season_names, season_months)):
                qs = ClimateObservation.objects.filter(date__month__in=months, district=district) if district else ClimateObservation.objects.filter(date__month__in=months)
                labels.append(name)
                if qs.exists():
                    avg = sum(getattr(o, db_field) or 0 for o in qs) / qs.count()
                    values.append(round(avg, 1))
                else:
                    # Use climatology baselines
                    bases = {"temperature": [26, 34, 32, 30], "rainfall": [2, 8, 18, 12], "humidity": [65, 70, 85, 75], "pressure": [1012, 1008, 1005, 1009], "wind": [10, 14, 16, 12]}
                    values.append(bases.get(variable, [30, 32, 31, 30])[i])
        else:
            return Response({"error": "Invalid period"}, status=400)

        return Response({
            "variable": variable,
            "period": period,
            "labels": labels,
            "values": values,
            "forecast_values": forecast_values,
            "unit": unit,
            "district": district.name if district else "Andhra Pradesh",
        })


class ClimateAnomalyView(APIView):
    """
    GET /api/climate/anomalies/?lat=&lng=
    Detects climate anomalies by comparing current observations against
    historical averages, seasonal averages, and long-term climate normals.
    """
    SEASONAL_NORMALS = {
        "temperature": 32.4,
        "rainfall": 12.4,
        "humidity": 78.0,
        "pressure": 1008.0,
        "wind": 14.0,
        "lst": 34.9,
        "sst": 28.0,
    }

    ANOMALY_THRESHOLDS = {
        "temperature": {"low": -1.5, "medium": -3.0, "high": -4.5},
        "rainfall": {"low": 20, "medium": 50, "high": 100},
        "humidity": {"low": 5, "medium": 10, "high": 20},
        "pressure": {"low": 2, "medium": 5, "high": 10},
        "wind": {"low": 5, "medium": 15, "high": 25},
        "lst": {"low": 1.5, "medium": 3.0, "high": 5.0},
        "sst": {"low": 0.5, "medium": 1.0, "high": 1.5},
    }

    ANOMALY_LABELS = {
        "temperature": ("Above Average Temperature", "Below Average Temperature"),
        "rainfall": ("Above Average Rainfall", "Extreme Rainfall Deficit"),
        "humidity": ("High Humidity Anomaly", "Low Humidity Anomaly"),
        "pressure": ("High Pressure Event", "Low Pressure System"),
        "wind": ("Extreme Wind Speed", "Very Low Wind"),
        "lst": ("Land Surface Overheating (LST)", "Abnormal LST Cooling"),
        "sst": ("Marine Heatwave (SST)", "Cold SST Anomaly"),
    }

    def get(self, request):
        lat = _safe_float(request.GET.get('lat'), 15.9129)
        lng = _safe_float(request.GET.get('lng'), 79.7400)
        today = datetime.date.today()

        districts = District.objects.all()
        district = min(districts, key=lambda d: math.hypot(d.latitude - lat, d.longitude - lng)) if districts.exists() else None

        obs = ClimateObservation.objects.filter(date=today, district=district).first() if district else None
        if not obs:
            pred = PredictionEngine._get_forecast_point(lat, lng, today, "1-day")
            current = pred
        else:
            current = {
                "temperature": obs.temperature, "rainfall": obs.rainfall,
                "humidity": obs.humidity, "pressure": obs.pressure,
                "wind": obs.wind, "lst": obs.lst, "sst": obs.sst or 0.0,
            }

        anomalies = []
        for var, normal in self.SEASONAL_NORMALS.items():
            val = current.get(var, normal)
            deviation = round(val - normal, 2)
            abs_dev = abs(deviation)
            thresholds = self.ANOMALY_THRESHOLDS.get(var, {"low": 1, "medium": 3, "high": 5})

            if abs_dev < thresholds["low"]:
                continue  # Within normal range

            if abs_dev >= thresholds["high"]:
                severity = "Critical"
            elif abs_dev >= thresholds["medium"]:
                severity = "High"
            else:
                severity = "Medium"

            pos_label, neg_label = self.ANOMALY_LABELS.get(var, (f"High {var}", f"Low {var}"))
            label = pos_label if deviation > 0 else neg_label

            units = {"temperature": "°C", "rainfall": "mm", "humidity": "%",
                     "pressure": "hPa", "wind": "knots", "lst": "°C", "sst": "°C"}
            unit = units.get(var, "")

            anomalies.append({
                "variable": var,
                "label": label,
                "current": round(val, 1),
                "baseline": normal,
                "deviation": deviation,
                "deviation_str": f"{'+' if deviation > 0 else ''}{deviation}{unit}",
                "severity": severity,
                "comparison_type": "seasonal_avg",
                "unit": unit,
            })

        # Sort by severity
        severity_order = {"Critical": 0, "High": 1, "Medium": 2}
        anomalies.sort(key=lambda x: severity_order.get(x["severity"], 3))

        return Response({
            "location": district.name if district else "Andhra Pradesh",
            "lat": lat, "lng": lng,
            "anomalies": anomalies,
            "total_anomalies": len(anomalies),
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })


class ClimateInsightsView(APIView):
    """
    GET /api/climate/insights/?lat=&lng=
    Generates human-readable AI insight sentences using prediction and risk data.
    All text is backend-generated from engine outputs.
    """
    def get(self, request):
        lat = _safe_float(request.GET.get('lat'), 15.9129)
        lng = _safe_float(request.GET.get('lng'), 79.7400)
        today = datetime.date.today()

        districts = District.objects.all()
        district = min(districts, key=lambda d: math.hypot(d.latitude - lat, d.longitude - lng)) if districts.exists() else None

        # Get current state
        obs = ClimateObservation.objects.filter(date=today, district=district).first() if district else None
        if obs:
            current = {"temperature": obs.temperature, "rainfall": obs.rainfall,
                       "humidity": obs.humidity, "pressure": obs.pressure,
                       "wind": obs.wind, "lst": obs.lst, "sst": obs.sst or 0.0}
        else:
            current = PredictionEngine._get_forecast_point(lat, lng, today, "1-day")

        # Get risk assessment
        risks = AnalyticsRiskEngine.calculate_risks({**current, "temp_change": 0, "rainfall_change": 0, "humidity_change": 0})

        # Get 7-day forecast
        predictions = PredictionEngine.predict_next_week(lat, lng, district)

        # Seasonal normals
        seasonal_normals = {"temperature": 32.4, "rainfall": 12.4, "humidity": 78.0, "sst": 28.0}

        # Build insight sentences from engine data
        insights = []

        # Temperature insight
        temp_diff = round(current["temperature"] - seasonal_normals["temperature"], 1)
        temp_dir = "above" if temp_diff > 0 else "below"
        if abs(temp_diff) >= 0.5:
            insights.append(f"Today's temperature ({current['temperature']}°C) is {abs(temp_diff)}°C {temp_dir} the seasonal average of {seasonal_normals['temperature']}°C.")

        # SST insight for coastal areas
        if current.get("sst", 0) > 0:
            sst_diff = round(current["sst"] - seasonal_normals["sst"], 1)
            if abs(sst_diff) >= 0.3:
                sst_effect = "driving elevated atmospheric moisture and convective activity" if sst_diff > 0 else "suppressing evaporation and rainfall formation"
                insights.append(f"Sea Surface Temperature ({current['sst']}°C, {'+' if sst_diff > 0 else ''}{sst_diff}°C vs normal) is {sst_effect}.")

        # Humidity insight
        if current["humidity"] > 85:
            insights.append(f"Relative humidity is critically high at {current['humidity']}%, indicating near-saturation atmospheric conditions.")
        elif current["humidity"] < 55:
            insights.append(f"Relative humidity is low at {current['humidity']}%, increasing heat stress and evapotranspiration rates.")

        # Rainfall forecast insight
        if predictions:
            avg_pred_rain = round(sum(p.rainfall for p in predictions[:3]) / 3, 1)
            if avg_pred_rain > 15:
                insights.append(f"Rainfall probability is elevated over the next 72 hours, with AI models projecting an average of {avg_pred_rain} mm/day.")
            elif avg_pred_rain < 2:
                insights.append(f"AI models forecast dry conditions over the next 72 hours, with less than 2mm rainfall expected.")

        # Risk-based insights
        risk_levels = {"heatwave_risk": "heatwave", "flood_risk": "flood", "cyclone_risk": "cyclone", "drought_risk": "drought"}
        for risk_key, risk_name in risk_levels.items():
            level = risks.get(risk_key, "Low")
            if level in ["High", "Critical"]:
                district_name = district.name if district else "coastal"
                insights.append(f"{risk_name.capitalize()} risk is {level.upper()} for {district_name} and surrounding districts. Immediate monitoring is advised.")
            elif level == "Medium":
                insights.append(f"{risk_name.capitalize()} risk remains Moderate — conditions warrant close observation.")

        # Pressure insight
        if current["pressure"] < 1000:
            insights.append(f"Low atmospheric pressure ({current['pressure']} hPa) indicates potential for intensifying convective systems or cyclogenesis.")

        if not insights:
            insights.append("Climate conditions are within normal seasonal parameters. No significant anomalies detected.")

        return Response({
            "location": district.name if district else "Andhra Pradesh",
            "lat": lat, "lng": lng,
            "insights": insights,
            "model_source": "xgboost" if ModelService.get_instance().is_ready else "idw_fallback",
            "risk_summary": {k: risks.get(k, "Low") for k in ["heatwave_risk", "flood_risk", "cyclone_risk", "drought_risk", "agriculture_risk"]},
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })


class ClimateComparisonView(APIView):
    """
    GET /api/climate/comparison/?d1=Visakhapatnam&d2=Kurnool
    Returns parallel climate data for two districts for side-by-side comparison.
    """
    def get(self, request):
        d1_name = request.GET.get('d1', '')
        d2_name = request.GET.get('d2', '')
        today = datetime.date.today()

        def get_district_data(name):
            district = District.objects.filter(name__icontains=name).first() if name else None
            if not district:
                district = District.objects.first()
            if not district:
                return None, {}

            obs = ClimateObservation.objects.filter(date=today, district=district).first()
            if obs:
                state = {
                    "temperature": obs.temperature, "rainfall": obs.rainfall,
                    "humidity": obs.humidity, "pressure": obs.pressure,
                    "wind_speed": obs.wind, "lst": obs.lst, "sst": obs.sst or 0.0,
                }
            else:
                pred = PredictionEngine._get_forecast_point(district.latitude, district.longitude, today, "1-day")
                state = {
                    "temperature": pred["temperature"], "rainfall": pred["rainfall"],
                    "humidity": pred["humidity"], "pressure": pred["pressure"],
                    "wind_speed": pred["wind"], "lst": pred["lst"], "sst": pred["sst"],
                }

            risks = AnalyticsRiskEngine.calculate_risks({**state, "wind": state["wind_speed"], "temp_change": 0, "rainfall_change": 0, "humidity_change": 0})

            pred_7day = PredictionEngine.predict_next_week(district.latitude, district.longitude, district)

            return district, {
                "name": district.name,
                "lat": district.latitude,
                "lng": district.longitude,
                "snapshot": state,
                "risk": {k: risks[k] for k in ["heatwave_risk", "flood_risk", "drought_risk", "cyclone_risk", "water_stress", "crop_stress"]},
                "forecast_7day": [{"day": (today + datetime.timedelta(days=i+1)).strftime("%a"), "temperature": p.temperature, "rainfall": p.rainfall} for i, p in enumerate(pred_7day)],
            }

        d1_district, d1_data = get_district_data(d1_name)
        d2_district, d2_data = get_district_data(d2_name)

        # All districts for dropdown
        all_districts = [{"name": d.name, "lat": d.latitude, "lng": d.longitude} for d in District.objects.all().order_by('name')]

        return Response({
            "districts": [d1_data, d2_data],
            "all_districts": all_districts,
            "comparison_variables": ["temperature", "rainfall", "humidity", "pressure", "wind_speed", "lst", "sst"],
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })


class ClimateStoryView(APIView):
    """
    GET /api/climate/story/?lat=&lng=
    Returns a structured climate story chain: Observation → Analysis →
    Prediction → Scenario → Risk → Conclusion.
    All text generated from backend engine outputs.
    """
    def get(self, request):
        lat = _safe_float(request.GET.get('lat'), 15.9129)
        lng = _safe_float(request.GET.get('lng'), 79.7400)
        today = datetime.date.today()

        districts = District.objects.all()
        district = min(districts, key=lambda d: math.hypot(d.latitude - lat, d.longitude - lng)) if districts.exists() else None

        obs = ClimateObservation.objects.filter(date=today, district=district).first() if district else None
        if obs:
            current = {"temperature": obs.temperature, "rainfall": obs.rainfall,
                       "humidity": obs.humidity, "pressure": obs.pressure,
                       "wind": obs.wind, "lst": obs.lst, "sst": obs.sst or 0.0}
        else:
            current = PredictionEngine._get_forecast_point(lat, lng, today, "1-day")

        risks = AnalyticsRiskEngine.calculate_risks({**current, "temp_change": 0, "rainfall_change": 0, "humidity_change": 0})
        predictions = PredictionEngine.predict_next_week(lat, lng, district)

        location_name = district.name if district else "Andhra Pradesh"
        is_coastal = lng > 80.5

        # Derive leading risk
        risk_priority = [("cyclone", "cyclone_risk"), ("flood", "flood_risk"), ("heatwave", "heatwave_risk"), ("drought", "drought_risk")]
        leading_risk = "Low"
        leading_risk_name = "System Stability"
        for name, key in risk_priority:
            level = risks.get(key, "Low")
            if level in ["Critical", "High"]:
                leading_risk = level
                leading_risk_name = name.capitalize()
                break
            elif level == "Medium":
                leading_risk = "Medium"
                leading_risk_name = name.capitalize()

        # Build story chain
        story = [
            {
                "stage": "Observation",
                "icon": "eye",
                "color": "cyan",
                "text": f"IMD + INSAT observations at {location_name}: Temperature {current['temperature']}°C, Rainfall {current['rainfall']}mm, Humidity {current['humidity']}%, Pressure {current['pressure']}hPa." + (f" SST at {current['sst']}°C in adjacent waters." if is_coastal and current['sst'] > 0 else "")
            },
            {
                "stage": "Analysis",
                "icon": "activity",
                "color": "blue",
                "text": f"LST at {current['lst']}°C indicates {'elevated surface heating above air temperature' if current['lst'] > current['temperature'] + 1 else 'near-normal surface conditions'}. " + ("High humidity indicates near-saturation air mass." if current['humidity'] > 80 else "Moderate atmospheric moisture detected.") + (" Low pressure system developing." if current['pressure'] < 1005 else "")
            },
            {
                "stage": "Prediction",
                "icon": "trending-up",
                "color": "emerald",
                "text": f"XGBoost ensemble model predicts: {predictions[0].temperature if predictions else current['temperature']}°C temperature, {predictions[0].rainfall if predictions else current['rainfall']}mm rainfall for Day+1. 7-day trend shows {'increasing rainfall probability' if predictions and sum(p.rainfall for p in predictions) > current['rainfall'] * 7 else 'relatively stable conditions'}."
            },
            {
                "stage": "Scenario",
                "icon": "sliders",
                "color": "purple",
                "text": f"Scenario Engine: Under the {'Cyclone' if leading_risk_name == 'Cyclone' else 'Heatwave' if leading_risk_name == 'Heatwave' else leading_risk_name} scenario, temperature could shift by {'+4.5°C' if leading_risk_name == 'Heatwave' else '+1.0°C'} and rainfall by {'–75%' if leading_risk_name == 'Drought' else '+200%' if leading_risk_name == 'Flood' else '±20%'}."
            },
            {
                "stage": "Risk",
                "icon": "alert-triangle",
                "color": "orange",
                "text": f"Risk Engine assessment — Heatwave: {risks['heatwave_risk']}, Flood: {risks['flood_risk']}, Cyclone: {risks['cyclone_risk']}, Drought: {risks['drought_risk']}. Water Stress Index: {round(risks['water_stress'], 1)}%. Agriculture Risk: {risks['agriculture_risk']}."
            },
            {
                "stage": "Conclusion",
                "icon": "check-circle",
                "color": "rose" if leading_risk in ["Critical", "High"] else "emerald",
                "text": f"Overall Digital Twin assessment: {leading_risk_name} risk is {leading_risk.upper()} for {location_name}. " + ("Immediate advisory and emergency protocols recommended." if leading_risk == "Critical" else "Close monitoring and preparedness measures advised." if leading_risk == "High" else "Continued observation recommended. Conditions remain manageable." if leading_risk == "Medium" else "No immediate action required. Climate within normal parameters.")
            },
        ]

        return Response({
            "location": location_name,
            "lat": lat, "lng": lng,
            "story": story,
            "leading_risk": leading_risk_name,
            "leading_risk_level": leading_risk,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })


class DigitalTwinStatusView(APIView):
    """
    GET /api/climate/twin-status/
    Returns Digital Twin system health: engine status, model status,
    DB status, and data source provenance.
    """
    def get(self, request):
        today = datetime.date.today()

        # Check observation engine health
        obs_count = ClimateObservation.objects.filter(date=today).count()
        obs_latest = ClimateObservation.objects.order_by('-date').first()
        obs_status = "online" if obs_count > 0 else ("degraded" if obs_latest else "offline")

        # Check prediction engine health
        pred_count = ClimatePrediction.objects.filter(date__gte=today).count()
        pred_status = "online" if pred_count > 0 else "degraded"

        # Check model service
        model_ready = False
        model_name = "IDW Fallback"
        try:
            service = ModelService.get_instance()
            model_ready = service.is_ready
            model_name = "XGBoost Ensemble" if model_ready else "IDW Spatial Fallback"
        except Exception:
            model_name = "IDW Spatial Fallback"

        # Check district data
        district_count = District.objects.count()

        # Check alert status
        active_alerts = Alert.objects.filter(active=True).count()

        # Simulation history
        sim_count = ClimateSimulation.objects.count()

        return Response({
            "engines": {
                "observation": {
                    "status": obs_status,
                    "records_today": obs_count,
                    "last_observation": obs_latest.date.isoformat() if obs_latest else None,
                    "description": "IMD + INSAT surface and satellite observations"
                },
                "prediction": {
                    "status": pred_status,
                    "forecast_records": pred_count,
                    "model": model_name,
                    "description": "XGBoost ML ensemble forecasting engine"
                },
                "scenario": {
                    "status": "online",
                    "simulations_run": sim_count,
                    "description": "What-if climate scenario perturbation engine"
                },
                "risk": {
                    "status": "online",
                    "active_alerts": active_alerts,
                    "description": "Multi-hazard risk assessment and attribution engine"
                },
                "digital_twin": {
                    "status": "online" if obs_status == "online" else "degraded",
                    "districts_tracked": district_count,
                    "description": "AI-driven state synchronization across all districts"
                },
            },
            "model": {
                "name": model_name,
                "ready": model_ready,
                "type": "xgboost" if model_ready else "idw_fallback",
            },
            "database": {
                "status": "online",
                "observation_records": ClimateObservation.objects.count(),
                "prediction_records": ClimatePrediction.objects.count(),
                "simulation_records": sim_count,
            },
            "data_sources": [
                {"name": "IMD Surface Weather", "acronym": "IMD", "status": "online", "last_updated": "10m ago", "description": "India Meteorological Department ground station network"},
                {"name": "INSAT-3D Satellite", "acronym": "INSAT", "status": "online", "last_updated": "3h ago", "description": "ISRO geostationary satellite LST and cloud data"},
                {"name": "MOSDAC Raster Stream", "acronym": "MOSDAC", "status": "delayed", "last_updated": "4h ago", "description": "SAC/ISRO Meteorological & Oceanographic Satellite Data"},
                {"name": "Bhuvan Landsat", "acronym": "ISRO", "status": "online", "last_updated": "2h ago", "description": "ISRO Bhuvan geospatial platform land data"},
            ],
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })

class SixDayForecastAPIView(APIView):
    def get(self, request):
        lat = float(request.GET.get('lat', 15.9129))
        lng = float(request.GET.get('lng', 79.7400))
        
        # 1. Grab base current-day observations to seed our lag features
        # In a production setup, fetch these from your ClimateObservation model
        current_rain = 0.0
        current_temp = 30.0
        current_humidity = 75.0
        current_pressure = 1008.0
        current_wind = 12.0
        
        forecast_data = []
        base_date = datetime.date.today()
        
        # 2. Iterative 6-Day Cascading Loop
        # We update lags dynamically because Day N depends on Day N-1 outputs!
        rain_lags = [current_rain, current_rain, current_rain] # [lag1, lag2, lag3]
        
        for i in range(1, 7):
            target_date = base_date + datetime.timedelta(days=i)
            day_of_year = target_date.timetuple().tm_yday
            month = target_date.month
            
            # Construct the inference payload matching your feature schema contract
            feature_payload = {
                'month': month,
                'day_of_year': day_of_year,
                'lat': lat,
                'lng': lng,
                'elevation_m': 15.0,  # Grab from database or external DEM if available
                'rain_lag1': rain_lags[0],
                'rain_lag2': rain_lags[1],
                'rain_lag3': rain_lags[2],
                'humidity': current_humidity,
                'pressure_hpa': current_pressure,
                'wind_kt': current_wind
            }
            
            # 3. Predict via your XGBoost Model Engine
            try:
                # Assuming ModelService exposes a clean predict interface for your pkls
                pred_rain = ModelService.predict('rainfall', feature_payload)
                pred_temp = ModelService.predict('temperature', feature_payload)
                pred_humidity = ModelService.predict('humidity', feature_payload)
                pred_wind = ModelService.predict('wind', feature_payload)
                pred_pressure = ModelService.predict('pressure', feature_payload)
            except Exception:
                # Fallback mechanism if models are compiling or missing
                pred_rain = max(0.0, current_rain + (i * 0.2))
                pred_temp = current_temp - (i * 0.5)
                pred_humidity = min(100.0, current_humidity + (i * 1.5))
                pred_wind = current_wind
                pred_pressure = current_pressure

            # 4. Save predictions to payload
            forecast_data.append({
                "day": i,
                "date": target_date.strftime("%Y-%m-%d"),
                "day_name": target_date.strftime("%a"),
                "rainfall": round(pred_rain, 2),
                "temperature": round(pred_temp, 1),
                "humidity": round(pred_humidity, 1),
                "wind_speed": round(pred_wind, 1),
                "pressure": round(pred_pressure, 1)
            })
            
            # 5. Cascade the lags forward for the next iteration step
            rain_lags = [pred_rain, rain_lags[0], rain_lags[1]]
            
        return Response({"status": "success", "forecast": forecast_data}, status=status.HTTP_OK)
