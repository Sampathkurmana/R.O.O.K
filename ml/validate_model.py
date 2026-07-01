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


if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

UNIFIED_FEATURES = ['Latitude', 'Longitude', 'DayOfYear', 'Is_Ocean', 'month_sin', 'month_cos']

def run_validation():
    from pathlib import Path
    models_dir = Path(__file__).parent / 'models'

    rain_path = models_dir / 'xgb_rainfall.pkl'
    temp_path = models_dir / 'xgb_temperature.pkl'
    humidity_path = models_dir / 'xgb_humidity.pkl'
    scaler_path = models_dir / 'feature_scaler.pkl'

    print('\n' + '='*75)
    print('  R.O.O.K — XGBoost Model Validation')
    print('='*75)

    # ── Check files exist ──────────────────────────────────────────
    print('\n[1] Checking model files...')
    missing_file = False
    for name, p in [('Rainfall', rain_path), ('Temperature', temp_path), ('Humidity', humidity_path)]:
        if not p.exists():
            print(f'  ❌ MISSING: {p}')
            print(f'     → Train and save: joblib.dump(model, "ml/models/xgb_{name.lower()}.pkl")')
            missing_file = True
        else:
            print(f'  ✅ xgb_{name.lower()}.pkl   found ({p.stat().st_size // 1024} KB)')
            
    if missing_file:
        return False

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
        humidity_model = joblib.load(humidity_path)
        scaler = joblib.load(scaler_path) if scaler_path.exists() else None
        print('  ✅ Models loaded successfully')
    except Exception as e:
        print(f'  ❌ Load error: {e}')
        return False

    # ── Validate feature schema ────────────────────────────────────
    print('\n[3] Checking feature compatibility...')
    
    def build_vec(lat, lng):
        day_of_year = 172
        is_ocean = 1 if lng > 83.2 else 0
        month = 6
        month_sin = math.sin(2 * math.pi * month / 12)
        month_cos = math.cos(2 * math.pi * month / 12)
        
        row = [lat, lng, day_of_year, is_ocean, month_sin, month_cos]
        X = np.array([row], dtype=np.float32)
        if scaler:
            X = scaler.transform(X)
        return X

    try:
        # Check model expects same number of features
        all_schemas_ok = True
        for m_name, model in [('Rainfall', rain_model), ('Temperature', temp_model), ('Humidity', humidity_model)]:
            try:
                n_feat = model.n_features_in_
                if n_feat != len(UNIFIED_FEATURES):
                    print(f'  ⚠️  {m_name} model expects {n_feat} features, schema has {len(UNIFIED_FEATURES)}')
                    all_schemas_ok = False
                else:
                    print(f'  ✅ {m_name} feature count matches model ({n_feat})')
            except AttributeError:
                print(f'  ℹ️  Cannot check n_features_in_ for {m_name} (model may not expose it)')

    except Exception as e:
        print(f'  ❌ Feature build error: {e}')
        return False

    # ── Run sample predictions ─────────────────────────────────────
    print('\n[4] Running sample predictions for 5 AP locations...')
    print(f'  {"Location":<20} {"Rain (mm)":>12} {"Tmax (°C)":>12} {"Humidity (%)":>14} {"Status":>10}')
    print('  ' + '-'*65)

    all_ok = True
    humidity_preds = []
    
    for (name, lat, lng) in TEST_LOCATIONS:
        try:
            X = build_vec(lat, lng)

            rain_pred = float(rain_model.predict(X)[0])
            temp_pred = temp_model.predict(X)[0]
            tmax = float(temp_pred[0]) if hasattr(temp_pred, '__len__') else float(temp_pred)
            humidity_pred = float(humidity_model.predict(X)[0])
            humidity_preds.append(humidity_pred)

            # Sanity checks
            ok = True
            if not (0 <= rain_pred <= 500):
                print(f'  ⚠️  Rainfall {rain_pred:.1f}mm out of plausible range [0–500]')
                ok = False
            if not (10 <= tmax <= 50):
                print(f'  ⚠️  Tmax {tmax:.1f}°C out of plausible range [10–50]')
                ok = False
            if not (0 <= humidity_pred <= 100):
                print(f'  ⚠️  Humidity {humidity_pred:.1f}% out of plausible range [0–100]')
                ok = False
            if math.isnan(rain_pred) or math.isinf(rain_pred):
                print(f'  ❌ NaN/Inf in rainfall prediction!')
                ok = False
            if math.isnan(tmax) or math.isinf(tmax):
                print(f'  ❌ NaN/Inf in temperature prediction!')
                ok = False
            if math.isnan(humidity_pred) or math.isinf(humidity_pred):
                print(f'  ❌ NaN/Inf in humidity prediction!')
                ok = False

            status = '✅ OK' if ok else '⚠️  CHECK'
            if not ok:
                all_ok = False
            print(f'  {name:<20} {rain_pred:>11.2f} {tmax:>11.1f} {humidity_pred:>13.1f} {status:>10}')

        except Exception as e:
            print(f'  {name:<20} {"ERROR":>12} {"ERROR":>12} {"ERROR":>14} {"❌":>10}  ({e})')
            all_ok = False

    # Check for flat humidity values
    if len(humidity_preds) == len(TEST_LOCATIONS):
        first_val = humidity_preds[0]
        is_flat = all(abs(h - first_val) < 1e-5 for h in humidity_preds)
        if is_flat:
            print(f'\n  ❌ FAILURE: Humidity prediction is identical across all locations ({first_val:.2f}%). Check clamping/features!')
            all_ok = False
        else:
            print(f'\n  ✅ Humidity predictions are distinct (range: {min(humidity_preds):.1f}% to {max(humidity_preds):.1f}%)')

    # ── Final verdict ──────────────────────────────────────────────
    print('\n' + '='*75)
    if all_ok:
        print('  ✅ All checks passed. Models are compatible with R.O.O.K.')
        print('  → Restart Django: python manage.py runserver')
        print('  → Real XGBoost predictions will activate immediately.')
    else:
        print('  ⚠️  Some checks had warnings or failures. Review output above.')
    print('='*75 + '\n')

    return all_ok


if __name__ == '__main__':
    success = run_validation()
    sys.exit(0 if success else 1)
