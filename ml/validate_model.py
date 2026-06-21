#!/usr/bin/env python
"""
ml/validate_model.py
=====================
Run this script BEFORE restarting Django after dropping in your model files.

Usage:
    python ml/validate_model.py

What it checks:
  ✅ .pkl files can be loaded
  ✅ Feature vector length matches schema
  ✅ Output shape and type are correct
  ✅ 5 sample AP locations produce plausible values
  ✅ No NaN or Inf in output
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rook.settings')

import numpy as np
import math

# Test locations: [name, lat, lng]
TEST_LOCATIONS = [
    ('Visakhapatnam', 17.69, 83.22),
    ('Kurnool',       15.83, 78.04),
    ('Guntur',        16.31, 80.45),
    ('Tirupati',      13.63, 79.42),
    ('Srikakulam',    18.30, 83.90),
]

TEST_FEATURES = {
    'month':        6,
    'day_of_year':  172,
    'elevation_m':  200.0,
    'rain_lag1':    8.0,
    'rain_lag2':    5.0,
    'rain_lag3':    3.0,
    'humidity':     72.0,
    'pressure_hpa': 1008.0,
    'wind_kt':      12.0,
    'tmax_lag1':    33.5,
    'tmin_lag1':    24.0,
    'tmax_lag2':    33.0,
    'tmin_lag2':    23.5,
    'month_sin':    math.sin(2 * math.pi * 6 / 12),
    'month_cos':    math.cos(2 * math.pi * 6 / 12),
    'olr':          230.0,
    'lst':          35.0,
}


def run_validation():
    from pathlib import Path
    models_dir = Path(__file__).parent / 'models'

    rain_path = models_dir / 'xgb_rainfall.pkl'
    temp_path = models_dir / 'xgb_temperature.pkl'
    scaler_path = models_dir / 'feature_scaler.pkl'

    print('\n' + '='*60)
    print('  R.O.O.K — XGBoost Model Validation')
    print('='*60)

    # ── Check files exist ──────────────────────────────────────────
    print('\n[1] Checking model files...')
    if not rain_path.exists():
        print(f'  ❌ MISSING: {rain_path}')
        print('     → Train and save: joblib.dump(model, "ml/models/xgb_rainfall.pkl")')
        return False
    if not temp_path.exists():
        print(f'  ❌ MISSING: {temp_path}')
        print('     → Train and save: joblib.dump(model, "ml/models/xgb_temperature.pkl")')
        return False

    print(f'  ✅ xgb_rainfall.pkl   found ({rain_path.stat().st_size // 1024} KB)')
    print(f'  ✅ xgb_temperature.pkl found ({temp_path.stat().st_size // 1024} KB)')
    if scaler_path.exists():
        print(f'  ✅ feature_scaler.pkl  found ({scaler_path.stat().st_size // 1024} KB)')
    else:
        print(f'  ℹ️  feature_scaler.pkl  not found (optional — OK if you did not scale features)')

    # ── Load models ────────────────────────────────────────────────
    print('\n[2] Loading models...')
    try:
        import joblib
        rain_model = joblib.load(rain_path)
        temp_model = joblib.load(temp_path)
        scaler = joblib.load(scaler_path) if scaler_path.exists() else None
        print('  ✅ Models loaded successfully')
    except Exception as e:
        print(f'  ❌ Load error: {e}')
        return False

    # ── Validate feature schema ────────────────────────────────────
    print('\n[3] Checking feature compatibility...')
    from ml.ap_feature_schema import RAINFALL_FEATURES, TEMPERATURE_FEATURES

    def build_vec(features, schema):
        vec = [features.get(f, 0.0) for f in schema]
        X = np.array(vec, dtype=np.float32).reshape(1, -1)
        if scaler:
            X = scaler.transform(X)
        return X

    try:
        X_rain = build_vec(TEST_FEATURES, RAINFALL_FEATURES)
        X_temp = build_vec(TEST_FEATURES, TEMPERATURE_FEATURES)
        print(f'  ✅ Rainfall feature vector: {X_rain.shape}  ({len(RAINFALL_FEATURES)} features)')
        print(f'  ✅ Temperature feature vector: {X_temp.shape}  ({len(TEMPERATURE_FEATURES)} features)')

        # Check model expects same number of features
        try:
            n_feat_rain = rain_model.n_features_in_
            n_feat_temp = temp_model.n_features_in_
            if n_feat_rain != len(RAINFALL_FEATURES):
                print(f'  ⚠️  Rainfall model expects {n_feat_rain} features, schema has {len(RAINFALL_FEATURES)}')
                print(f'     → Retrain with exactly the features in ml/ap_feature_schema.py')
            else:
                print(f'  ✅ Rainfall feature count matches model ({n_feat_rain})')
            if n_feat_temp != len(TEMPERATURE_FEATURES):
                print(f'  ⚠️  Temperature model expects {n_feat_temp} features, schema has {len(TEMPERATURE_FEATURES)}')
            else:
                print(f'  ✅ Temperature feature count matches model ({n_feat_temp})')
        except AttributeError:
            print('  ℹ️  Cannot check n_features_in_ (model may not expose it)')

    except Exception as e:
        print(f'  ❌ Feature build error: {e}')
        return False

    # ── Run sample predictions ─────────────────────────────────────
    print('\n[4] Running sample predictions for 5 AP locations...')
    print(f'  {"Location":<20} {"Rain (mm)":>12} {"Tmax (°C)":>12} {"Status":>10}')
    print('  ' + '-'*55)

    all_ok = True
    for (name, lat, lng) in TEST_LOCATIONS:
        features = {**TEST_FEATURES, 'lat': lat, 'lng': lng}
        try:
            X_r = build_vec(features, RAINFALL_FEATURES)
            X_t = build_vec(features, TEMPERATURE_FEATURES)

            rain_pred = float(rain_model.predict(X_r)[0])
            temp_pred = temp_model.predict(X_t)[0]
            tmax = float(temp_pred[0]) if hasattr(temp_pred, '__len__') else float(temp_pred)

            # Sanity checks
            ok = True
            if not (0 <= rain_pred <= 500):
                print(f'  ⚠️  Rainfall {rain_pred:.1f}mm out of plausible range [0–500]')
                ok = False
            if not (10 <= tmax <= 50):
                print(f'  ⚠️  Tmax {tmax:.1f}°C out of plausible range [10–50]')
                ok = False
            if math.isnan(rain_pred) or math.isinf(rain_pred):
                print(f'  ❌ NaN/Inf in rainfall prediction!')
                ok = False
            if math.isnan(tmax) or math.isinf(tmax):
                print(f'  ❌ NaN/Inf in temperature prediction!')
                ok = False

            status = '✅ OK' if ok else '⚠️  CHECK'
            if not ok:
                all_ok = False
            print(f'  {name:<20} {rain_pred:>11.2f} {tmax:>11.1f} {status:>10}')

        except Exception as e:
            print(f'  {name:<20} {"ERROR":>12} {"ERROR":>12} {"❌":>10}  ({e})')
            all_ok = False

    # ── Final verdict ──────────────────────────────────────────────
    print('\n' + '='*60)
    if all_ok:
        print('  ✅ All checks passed. Models are compatible with R.O.O.K.')
        print('  → Restart Django: python manage.py runserver')
        print('  → Real XGBoost predictions will activate immediately.')
    else:
        print('  ⚠️  Some checks had warnings. Review output above.')
        print('     Models may still work — check plausibility for your data range.')
    print('='*60 + '\n')

    return all_ok


if __name__ == '__main__':
    success = run_validation()
    sys.exit(0 if success else 1)
