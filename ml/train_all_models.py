import pandas as pd
import numpy as np
import xgboost as xgb
import math
import os
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# Add project root to path to import ap_feature_schema
import sys
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
from ml.ap_feature_schema import RAINFALL_FEATURES, TEMPERATURE_FEATURES, AP_STATION_ELEVATIONS

def main():
    dataset_path = Path(__file__).resolve().parent / "datasets" / "dataset.csv"
    models_dir = Path(__file__).resolve().parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading dataset from {dataset_path}...")
    df = pd.read_csv(dataset_path)
    print(f"Loaded {len(df):,} rows.")

    # 1. Parse Date and sort for correct lag calculations
    print("Parsing dates and sorting dataset...")
    df['date_parsed'] = pd.to_datetime(df['Date'], format='%d-%m-%Y', errors='coerce')
    df = df.sort_values(by=['Latitude', 'Longitude', 'date_parsed'])

    # 2. Build Lags grouped by station location
    print("Computing lag features per coordinate station...")
    grouped = df.groupby(['Latitude', 'Longitude'])

    df['rain_lag1'] = grouped['Rainfall'].shift(1)
    df['rain_lag2'] = grouped['Rainfall'].shift(2)
    df['rain_lag3'] = grouped['Rainfall'].shift(3)

    df['tmax_lag1'] = grouped['Temperature'].shift(1)
    df['tmax_lag2'] = grouped['Temperature'].shift(2)
    df['tmin_lag1'] = grouped['Temperature'].shift(1) - 5.0
    df['tmin_lag2'] = grouped['Temperature'].shift(2) - 5.0

    # 3. Map features to schema names
    print("Mapping columns and seasonal encodings...")
    df['lat'] = df['Latitude']
    df['lng'] = df['Longitude']
    df['humidity'] = df['Humidity']
    df['pressure_hpa'] = df['Surface_Pressure_hPa']
    df['wind_kt'] = df['WindSpeed']

    df['month_sin'] = df['Month'].apply(lambda m: math.sin(2 * math.pi * m / 12))
    df['month_cos'] = df['Month'].apply(lambda m: math.cos(2 * math.pi * m / 12))
    df['day_of_year'] = df['DayOfYear']

    # 4. Lookup Elevation
    print("Looking up station elevations...")
    def get_elevation(lat, lng):
        closest_elev = 150.0
        min_dist = float('inf')
        for station, (s_lat, s_lng, elev) in AP_STATION_ELEVATIONS.items():
            dist = math.hypot(lat - s_lat, lng - s_lng)
            if dist < min_dist:
                min_dist = dist
                closest_elev = elev
        if min_dist < 0.5:
            return closest_elev
        return 150.0

    # Cache unique coordinates to speed up elevation mapping
    unique_coords = df[['Latitude', 'Longitude']].drop_duplicates()
    elev_map = {}
    for _, row in unique_coords.iterrows():
        lat, lng = row['Latitude'], row['Longitude']
        elev_map[(lat, lng)] = get_elevation(lat, lng)

    df['elevation_m'] = df.apply(lambda r: elev_map[(r['Latitude'], r['Longitude'])], axis=1)

    # 5. Drop NaN rows resulting from shifts
    df = df.dropna(subset=['rain_lag1', 'rain_lag2', 'rain_lag3', 'tmax_lag1', 'tmax_lag2', 'Rainfall', 'Temperature'])
    print(f"Cleaned dataset has {len(df):,} rows.")

    # 6. Train Rainfall Model
    print("\nTraining XGBoost Rainfall Model...")
    X_rain = df[RAINFALL_FEATURES]
    y_rain = df['Rainfall']
    
    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X_rain, y_rain, test_size=0.2, random_state=42)
    
    rain_model = xgb.XGBRegressor(
        n_estimators=150,
        learning_rate=0.08,
        max_depth=6,
        random_state=42,
        objective='reg:squarederror'
    )
    rain_model.fit(X_train_r, y_train_r)
    
    preds_r = rain_model.predict(X_test_r)
    rmse_r = np.sqrt(mean_squared_error(y_test_r, preds_r))
    print(f"Rainfall Model RMSE: {rmse_r:.3f} mm")

    # 7. Train Temperature Model
    print("\nTraining XGBoost Temperature Model...")
    X_temp = df[TEMPERATURE_FEATURES]
    y_temp = df['Temperature'] # using Temperature as target Tmax
    
    X_train_t, X_test_t, y_train_t, y_test_t = train_test_split(X_temp, y_temp, test_size=0.2, random_state=42)
    
    temp_model = xgb.XGBRegressor(
        n_estimators=150,
        learning_rate=0.08,
        max_depth=6,
        random_state=42,
        objective='reg:squarederror'
    )
    temp_model.fit(X_train_t, y_train_t)
    
    preds_t = temp_model.predict(X_test_t)
    rmse_t = np.sqrt(mean_squared_error(y_test_t, preds_t))
    print(f"Temperature Model RMSE: {rmse_t:.3f} °C")

    # 8. Save Model weights
    rain_path = models_dir / "xgb_rainfall.pkl"
    temp_path = models_dir / "xgb_temperature.pkl"
    
    joblib.dump(rain_model, rain_path)
    joblib.dump(temp_model, temp_path)
    print(f"\n✅ Saved Rainfall model to {rain_path}")
    print(f"✅ Saved Temperature model to {temp_path}")

    # 9. Update model metadata
    from datetime import datetime
    meta = {
        'loaded_at': datetime.utcnow().isoformat(),
        'rainfall_model': 'xgb_rainfall.pkl',
        'temperature_model': 'xgb_temperature.pkl',
        'scaler': None,
        'schema_version': '1.0',
    }
    with open(models_dir / 'model_meta.json', 'w') as f:
        json.dump(meta, f, indent=2)
    print("✅ Updated model_meta.json")

if __name__ == '__main__':
    import json
    main()
