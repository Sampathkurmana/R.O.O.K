"""
ml/train_xgboost.py
====================
Reference training script for R.O.O.K XGBoost models.
Run this externally on your dataset, then copy the .pkl files to ml/models/.

Usage:
    python ml/train_xgboost.py --data data/ap_imd_historical.csv --output ml/models/

Requirements:
    pip install xgboost scikit-learn pandas numpy joblib
"""

import argparse
import math
import os
import sys

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# We are using a unified feature set so the Django cascading loop is easy.
# These match the features we agreed are "knowable" in the future.
UNIFIED_FEATURES = [
    'Latitude', 'Longitude', 'DayOfYear', 'Is_Ocean'
]

# # ── Feature Schema (must match ml/ap_feature_schema.py) ───────────────────────
# RAINFALL_FEATURES = [
#     'month', 'day_of_year', 'lat', 'lng', 'elevation_m',
#     'rain_lag1', 'rain_lag2', 'rain_lag3',
#     'humidity', 'pressure_hpa', 'wind_kt',
#     'month_sin', 'month_cos',
#     # Uncomment if INSAT data available:
#     # 'olr',
# ]

# TEMPERATURE_FEATURES = [
#     'month', 'day_of_year', 'lat', 'lng', 'elevation_m',
#     'tmax_lag1', 'tmin_lag1', 'tmax_lag2', 'tmin_lag2',
#     'humidity', 'pressure_hpa',
#     'month_sin', 'month_cos',
#     # Uncomment if INSAT LST available:
#     # 'lst',
# ]


def feature_engineer(df: pd.DataFrame) -> pd.DataFrame:
    """Add seasonal encodings to the dataframe."""
    df = df.copy()
    
    # Ensure Date is parsed
    if 'Date' in df.columns and df['Date'].dtype == 'object':
        df['Date'] = pd.to_datetime(df['Date'])
    
    if 'Date' in df.columns:
        # 🔥 THE FIX: Force Pandas to convert to Datetime, day-first format!
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        
        # Now Pandas knows it's a date, so .dt will work perfectly
        df['month'] = df['Date'].dt.month
        df['month_sin'] = df['month'].apply(lambda m: math.sin(2 * math.pi * m / 12))
        df['month_cos'] = df['month'].apply(lambda m: math.cos(2 * math.pi * m / 12))
        
        # Add them to our unified features!
        if 'month_sin' not in UNIFIED_FEATURES:
            UNIFIED_FEATURES.extend(['month_sin', 'month_cos'])
            
    return df

def train_generic_model(df: pd.DataFrame, target_col: str, output_dir: str, scale: bool = False, scaler=None):
    """A generic trainer for ANY target column (Wind, Temp, Pressure, etc.)"""
    print(f'\n=== Training Model for: {target_col} ===')
    
    # Drop rows where the target is missing (Crucial for SST/LST)
    clean_df = df.dropna(subset=[target_col])
    
    X = clean_df[UNIFIED_FEATURES]
    y = clean_df[target_col]

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

    if scale and scaler is None:
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X_tr)
        X_te = scaler.transform(X_te)
        joblib.dump(scaler, os.path.join(output_dir, f'feature_scaler_{target_col}.pkl'))
    elif scaler is not None:
        X_tr = scaler.transform(X_tr)
        X_te = scaler.transform(X_te)

    # Using your teammate's tuned parameters
    model = xgb.XGBRegressor(
        n_estimators=500,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        objective='reg:squarederror',
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=20,
        eval_metric='rmse',
        enable_categorical=False 
    )

    model.fit(
        X_tr, y_tr,
        eval_set=[(X_te, y_te)],
        verbose=False # Set to false so it doesn't spam your terminal 500 times
    )

    y_pred = model.predict(X_te)
    rmse   = np.sqrt(mean_squared_error(y_te, y_pred))
    mae    = mean_absolute_error(y_te, y_pred)
    r2     = r2_score(y_te, y_pred)

    print(f'  RMSE : {rmse:.3f}')
    print(f'  MAE  : {mae:.3f}')
    print(f'  R²   : {r2:.4f}')

    out_path = os.path.join(output_dir, f'xgb_{target_col.lower()}.pkl')
    joblib.dump(model, out_path)
    print(f'  [OK] Saved -> {out_path}')

    return model, scaler


def main():
    parser = argparse.ArgumentParser(description='Train R.O.O.K XGBoost models')
    parser.add_argument('--data',   required=True,          help='Path to dataset.csv')
    parser.add_argument('--output', default='ml/models/',   help='Output directory for .pkl files')
    parser.add_argument('--scale',  action='store_true',    help='Apply StandardScaler to features')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print(f'Loading data from {args.data}...')
    df = pd.read_csv(args.data)
    print(f'  Rows loaded: {len(df):,}')

    print('Feature engineering...')
    df = feature_engineer(df)
    
    # 🎯 The targets we want to train (Make sure these match your CSV exactly!)
    targets = ['Rainfall', 'Temperature', 'Humidity', 'Surface_Pressure_hPa', 'WindSpeed']
    
    # Optionally add SST and LST if they exist in your Exodia dataset
    if 'SST' in df.columns: targets.append('SST')
    if 'LST' in df.columns: targets.append('LST')

    global_scaler = None
    
    for target in targets:
        if target in df.columns:
            # We train each model iteratively
            model, global_scaler = train_generic_model(df, target, args.output, scale=args.scale, scaler=global_scaler)
        else:
            print(f"\n[WARN] Skipping {target}: Not found in dataset columns.")

    print('\n' + '='*55)
    print('  [OK] All Training complete. Files saved to:', args.output)
    print('='*55 + '\n')


if __name__ == '__main__':
    main()