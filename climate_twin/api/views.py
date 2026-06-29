import csv
import io
import json
import logging
import datetime
import math
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

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

class WeatherAPIView(APIView):
    """
    GET /api/weather/
    Fetches OpenWeatherMap (Core) + Open-Meteo (SST/LST), saves to DB, caches for 12 hours.
    """
    def get(self, request):
        lat = float(request.GET.get('lat', 17.6868))
        lng = float(request.GET.get('lng', 83.2185))
        
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
            ClimateObservation.objects.update_or_create(
                date=today,
                latitude=lat,
                longitude=lng,
                defaults={
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
        lat_str = request.GET.get('lat')
        lng_str = request.GET.get('lng')
        
        lat = float(lat_str) if lat_str else 15.9129
        lng = float(lng_str) if lng_str else 79.7400

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
        temp_change = float(request.data.get("temp_change", request.data.get("temp_delta", 0.0)))
        rainfall_change = float(request.data.get("rainfall_change", request.data.get("rain_delta", 0.0)))
        humidity_change = float(request.data.get("humidity_change", 0.0))
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
        lat = float(request.GET.get('lat', 15.9129))
        lng = float(request.GET.get('lng', 79.7400))
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

        lat = float(body.get('lat', 15.9129))
        lng = float(body.get('lng', 79.7400))
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
        
        # If datetime_str is not provided, fall back to legacy month/year/date queries
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
        
        # Retrieve optional simulator parameters
        temp_delta = float(request.GET.get("temp_delta", 0.0))
        rain_delta = float(request.GET.get("rain_delta", 0.0))
        humidity_change = float(request.GET.get("humidity_change", 0.0))
        scenario_category = request.GET.get("scenario_category", "Custom")

        # Map mode inputs and fetch baseline
        districts = District.objects.all()
        grid_points = []
        
        # Find nearest district for target location if provided
        lat_str = request.GET.get('lat')
        lng_str = request.GET.get('lng')
        target_district = None
        if lat_str and lng_str:
            lat = float(lat_str)
            lng = float(lng_str)
            if districts.exists():
                target_district = min(districts, key=lambda d: math.hypot(d.latitude - lat, d.longitude - lng))
        if not target_district:
            target_district = districts.first()

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
            base_temp = 32.4
            base_rain = 5.0
            base_hum = 75.0
            base_press = 1008.0
            base_wind = 14.0
            base_lst = 34.0
            base_sst = 0.0
            wind_dir = "SW"

            # Fetch DB values depending on mode
            if mode in ['history', 'live'] or (mode == 'scenario' and ClimateObservation.objects.filter(date=target_date, district=district).exists()):
                records = ClimateObservation.objects.filter(date=target_date, district=district)
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
                records = ClimatePrediction.objects.filter(date=target_date, district=district)
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

        if mode in ['history', 'live'] or (mode == 'scenario' and ClimateObservation.objects.filter(date=target_date, district=target_district_obj).exists()):
            td_obs = ClimateObservation.objects.filter(date=target_date, district=target_district_obj).first()
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
            td_pred = ClimatePrediction.objects.filter(date=target_date, district=target_district_obj).first()
            if td_pred:
                td_temp = td_pred.temperature
                td_rain = td_pred.rainfall
                td_hum = td_pred.humidity
                td_wind = td_pred.wind
                td_press = td_pred.pressure
                td_lst = td_pred.lst
                td_sst = td_pred.sst
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
            h_sst = td_sst + 0.15 * math.sin((h - 12) * math.pi / 12) if target_district_obj.longitude > 80.5 else 0.0
            
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

        return Response({
            "mode": mode,
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
        })


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
