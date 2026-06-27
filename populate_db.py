import os
import django
import datetime
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climate_twin.settings')
django.setup()

from climate_twin.models import State, District, ClimateObservation, ClimatePrediction, Alert

# District stations list with coordinate mappings
DISTRICT_STATIONS = [
    { "name": "Anantapur", "lat": 14.6819, "lng": 77.6006, "temp": 34.2, "rain": 2.1, "hum": 55, "pressure": 1008, "wind": 15 },
    { "name": "Chittoor", "lat": 13.2172, "lng": 79.1003, "temp": 32.0, "rain": 4.5, "hum": 68, "pressure": 1009, "wind": 12 },
    { "name": "East Godavari", "lat": 17.2305, "lng": 81.8282, "temp": 31.8, "rain": 22.4, "hum": 88, "pressure": 1007, "wind": 22 },
    { "name": "Guntur", "lat": 16.3067, "lng": 80.4365, "temp": 33.5, "rain": 11.2, "hum": 75, "pressure": 1007, "wind": 18 },
    { "name": "Krishna", "lat": 16.1667, "lng": 81.1333, "temp": 32.9, "rain": 14.8, "hum": 82, "pressure": 1008, "wind": 20 },
    { "name": "Kurnool", "lat": 15.8281, "lng": 78.0373, "temp": 35.1, "rain": 1.0, "hum": 52, "pressure": 1009, "wind": 14 },
    { "name": "Prakasam", "lat": 15.5057, "lng": 79.6450, "temp": 33.8, "rain": 3.2, "hum": 64, "pressure": 1010, "wind": 16 },
    { "name": "Srikakulam", "lat": 18.2949, "lng": 83.8938, "temp": 30.5, "rain": 28.6, "hum": 92, "pressure": 1006, "wind": 25 },
    { "name": "Nellore", "lat": 14.4426, "lng": 79.9865, "temp": 33.0, "rain": 5.1, "hum": 70, "pressure": 1011, "wind": 17 },
    { "name": "Visakhapatnam", "lat": 17.6868, "lng": 83.2185, "temp": 31.2, "rain": 18.5, "hum": 85, "pressure": 1006, "wind": 24 },
    { "name": "Vizianagaram", "lat": 18.1124, "lng": 83.3989, "temp": 30.9, "rain": 21.0, "hum": 89, "pressure": 1006, "wind": 21 },
    { "name": "West Godavari", "lat": 16.8105, "lng": 81.4288, "temp": 32.1, "rain": 19.3, "hum": 86, "pressure": 1008, "wind": 19 },
    { "name": "YSR Kadapa", "lat": 14.4673, "lng": 78.8242, "temp": 34.6, "rain": 1.8, "hum": 58, "pressure": 1009, "wind": 13 }
]

def seed_data():
    print("Flushing existing database tables...")
    ClimateObservation.objects.all().delete()
    ClimatePrediction.objects.all().delete()
    Alert.objects.all().delete()
    District.objects.all().delete()
    State.objects.all().delete()

    print("Creating State Andhra Pradesh...")
    state, _ = State.objects.get_or_create(name="Andhra Pradesh")

    print("Creating Districts...")
    district_map = {}
    for station in DISTRICT_STATIONS:
        district = District.objects.create(
            name=station["name"],
            state=state,
            latitude=station["lat"],
            longitude=station["lng"]
        )
        district_map[station["name"]] = district

    print("Generating Climate Observation history (past 30 days)...")
    today = datetime.date.today()
    observations_to_create = []

    for day_offset in range(30):
        obs_date = today - datetime.timedelta(days=day_offset)
        # Seed for each district station
        for station in DISTRICT_STATIONS:
            district_obj = district_map[station["name"]]
            # Introduce slight daily variance
            temp_var = random.uniform(-1.5, 1.5)
            rain_var = random.uniform(-3.0, 5.0)
            hum_var = random.uniform(-5.0, 5.0)

            final_temp = round(station["temp"] + temp_var, 1)
            final_rain = round(max(0.0, station["rain"] + rain_var), 1)
            final_hum = round(min(100.0, max(10.0, station["hum"] + hum_var)), 1)
            
            # Surface temperature estimates
            final_lst = round(final_temp + 2.5 + random.uniform(-0.5, 0.5), 1)
            final_sst = round(final_temp - 2.8 + random.uniform(-0.3, 0.3), 1) if station["lng"] > 80.5 else 0.0

            observations_to_create.append(
                ClimateObservation(
                    date=obs_date,
                    district=district_obj,
                    latitude=station["lat"],
                    longitude=station["lng"],
                    temperature=final_temp,
                    rainfall=final_rain,
                    humidity=final_hum,
                    pressure=station["pressure"] + random.randint(-2, 2),
                    wind=round(random.uniform(8.0, 25.0), 1),
                    lst=final_lst,
                    sst=final_sst,
                    wind_speed=round(random.uniform(8.0, 25.0), 1),
                    wind_direction=random.choice(["SW", "WSW", "SSW", "WNW", "S"])
                )
            )
    
    ClimateObservation.objects.bulk_create(observations_to_create)
    print(f"Created {len(observations_to_create)} historical observation records.")

    print("Generating AI Prediction data (next 7 days)...")
    predictions_to_create = []
    for day_offset in range(7):
        pred_date = today + datetime.timedelta(days=day_offset + 1)
        for station in DISTRICT_STATIONS:
            district_obj = district_map[station["name"]]
            
            pred_temp = round(station["temp"] + random.uniform(-1.0, 1.5), 1)
            pred_rain = round(max(0.0, station["rain"] + random.uniform(-3.0, 4.0)), 1)
            pred_hum = round(min(100.0, max(10.0, station["hum"] + random.uniform(-5.0, 5.0))), 1)
            
            predictions_to_create.append(
                ClimatePrediction(
                    date=pred_date,
                    district=district_obj,
                    latitude=station["lat"],
                    longitude=station["lng"],
                    rainfall=pred_rain,
                    temperature=pred_temp,
                    humidity=pred_hum,
                    pressure=station["pressure"],
                    wind=round(random.uniform(10.0, 20.0), 1),
                    lst=round(pred_temp + 2.5, 1),
                    sst=round(pred_temp - 2.8, 1) if station["lng"] > 80.5 else 0.0,
                    prediction_confidence=round(random.uniform(0.75, 0.95), 2),
                    horizon="7-day" if day_offset >= 3 else ("3-day" if day_offset >= 1 else "1-day"),
                    
                    # Aliases for compatibility
                    rainfall_prediction=pred_rain,
                    temperature_prediction=pred_temp,
                    humidity_prediction=pred_hum,
                    wind_speed_prediction=round(random.uniform(10.0, 20.0), 1)
                )
            )
    ClimatePrediction.objects.bulk_create(predictions_to_create)
    print(f"Created {len(predictions_to_create)} predictive outlook records.")

    print("Generating active climate alerts...")
    alerts = [
        Alert(
            type="Cyclone",
            severity="Critical",
            district="Visakhapatnam & East Godavari Coast",
            description="Severe Cyclonic Storm warnings issued for coastal areas. Winds expected to exceed 65 knots with wave heights up to 4.5m."
        ),
        Alert(
            type="Heatwave",
            severity="High",
            district="Kurnool & Anantapur",
            description="High temperature anomalies exceeding +4.5C above seasonal averages. Public advisory issued for severe thermal exposure."
        ),
        Alert(
            type="Flood",
            severity="Medium",
            district="Krishna Basin Lowlands",
            description="Heavy rainfall predictions upstream triggers reservoir alerts. Runoff discharge levels rising."
        ),
        Alert(
            type="Drought",
            severity="Low",
            district="Rayalaseema Region",
            description="Prolonged dry spell observations indicate low soil moisture availability across rural farmlands."
        )
    ]
    Alert.objects.bulk_create(alerts)
    print("Created 4 warning alert items.")
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_data()
