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

# ── Feature Schema (must match ml/ap_feature_schema.py) ───────────────────────
RAINFALL_FEATURES = [
    'month', 'day_of_year', 'lat', 'lng', 'elevation_m',
    'rain_lag1', 'rain_lag2', 'rain_lag3',
    'humidity', 'pressure_hpa', 'wind_kt',
    'month_sin', 'month_cos',
    # Uncomment if INSAT data available:
    # 'olr',
]

TEMPERATURE_FEATURES = [
    'month', 'day_of_year', 'lat', 'lng', 'elevation_m',
    'tmax_lag1', 'tmin_lag1', 'tmax_lag2', 'tmin_lag2',
    'humidity', 'pressure_hpa',
    'month_sin', 'month_cos',
    # Uncomment if INSAT LST available:
    # 'lst',
]


def feature_engineer(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag features and seasonal encodings to the dataframe."""
    df = df.copy()
    df['date']        = pd.to_datetime(df['date'])
    df['month']       = df['date'].dt.month
    df['day_of_year'] = df['date'].dt.dayofyear
    df['month_sin']   = df['month'].apply(lambda m: math.sin(2 * math.pi * m / 12))
    df['month_cos']   = df['month'].apply(lambda m: math.cos(2 * math.pi * m / 12))

    # Lag features (per station, not globally)
    for col, lags in [('rainfall_mm', [1, 2, 3]),
                      ('tmax_c',      [1, 2]),
                      ('tmin_c',      [1, 2])]:
        for lag in lags:
            lag_col = f'{col.split("_")[0]}_lag{lag}' if 'rain' in col else f't{"max" if "max" in col else "min"}_lag{lag}'
            df[lag_col] = df.groupby('station_id')[col].shift(lag)

    df.dropna(inplace=True)
    return df


def train_rainfall_model(df: pd.DataFrame, output_dir: str, scale: bool = False):
    """Train XGBoost rainfall model and save to output_dir."""
    print('\n── Training Rainfall Model ──────────────────────────────')
    X = df[RAINFALL_FEATURES]
    y = df['rainfall_mm']

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = None
    if scale:
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X_tr)
        X_te = scaler.transform(X_te)
        joblib.dump(scaler, os.path.join(output_dir, 'feature_scaler.pkl'))
        print('  Scaler saved → feature_scaler.pkl')

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
    )

    model.fit(
        X_tr, y_tr,
        eval_set=[(X_te, y_te)],
        verbose=50
    )

    y_pred = model.predict(X_te)
    rmse   = mean_squared_error(y_te, y_pred, squared=False)
    r2     = r2_score(y_te, y_pred)

    print(f'\n  Rainfall RMSE : {rmse:.3f} mm  (target < 8 mm)')
    print(f'  Rainfall R²   : {r2:.4f}       (target > 0.75)')

    out_path = os.path.join(output_dir, 'xgb_rainfall.pkl')
    joblib.dump(model, out_path)
    print(f'  ✅ Saved → {out_path}')

    return model, scaler


def train_temperature_model(df: pd.DataFrame, output_dir: str, scaler=None):
    """Train XGBoost temperature model (Tmax) and save to output_dir."""
    print('\n── Training Temperature Model ───────────────────────────')
    X = df[TEMPERATURE_FEATURES]
    y = df['tmax_c']

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

    if scaler is not None:
        X_tr = scaler.transform(X_tr)
        X_te = scaler.transform(X_te)

    model = xgb.XGBRegressor(
        n_estimators=500,
        max_depth=8,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        objective='reg:squarederror',
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=20,
        eval_metric='rmse',
    )

    model.fit(
        X_tr, y_tr,
        eval_set=[(X_te, y_te)],
        verbose=50
    )

    y_pred = model.predict(X_te)
    mae  = mean_absolute_error(y_te, y_pred)
    r2   = r2_score(y_te, y_pred)

    print(f'\n  Temperature MAE : {mae:.3f} °C  (target < 1.5 °C)')
    print(f'  Temperature R²  : {r2:.4f}       (target > 0.88)')

    out_path = os.path.join(output_dir, 'xgb_temperature.pkl')
    joblib.dump(model, out_path)
    print(f'  ✅ Saved → {out_path}')

    return model


def main():
    parser = argparse.ArgumentParser(description='Train R.O.O.K XGBoost models')
    parser.add_argument('--data',   required=True,          help='Path to ap_imd_historical.csv')
    parser.add_argument('--output', default='ml/models/',   help='Output directory for .pkl files')
    parser.add_argument('--scale',  action='store_true',    help='Apply StandardScaler to features')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print(f'Loading data from {args.data}...')
    df = pd.read_csv(args.data)
    print(f'  Rows loaded: {len(df):,}')

    print('Feature engineering...')
    df = feature_engineer(df)
    print(f'  Rows after feature engineering: {len(df):,}')

    rain_model, scaler = train_rainfall_model(df, args.output, scale=args.scale)
    temp_model          = train_temperature_model(df, args.output, scaler=scaler)

    print('\n' + '='*55)
    print('  ✅ Training complete. Files saved to:', args.output)
    print('  Next: python ml/validate_model.py')
    print('='*55 + '\n')


if __name__ == '__main__':
    main()
