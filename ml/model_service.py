"""
ml/model_service.py
====================
Plug-and-Play XGBoost Model Service for R.O.O.K.

Usage:
  1. Drop your trained .pkl files into ml/models/
  2. This service auto-discovers and loads them on first call.
  3. Falls back to IDW spatial interpolation if no models found.

DO NOT edit the inference path below unless you change ap_feature_schema.py.
"""

import os
import math
import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger('rook.ml')

MODELS_DIR = Path(__file__).parent / 'models'


class ModelService:
    """
    Singleton that loads XGBoost models once and serves predictions.
    
    Models expected in ml/models/:
        xgb_rainfall.pkl        — XGBoost rainfall regressor
        xgb_temperature.pkl     — XGBoost temperature regressor
        feature_scaler.pkl      — (optional) StandardScaler fitted on training data
    """
    _instance = None
    _rainfall_model = None
    _temperature_model = None
    _scaler = None
    _ready = False
    _model_meta = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_models()
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    # ─────────────────────────────────────────────────────────────────────────
    # Model Loading
    # ─────────────────────────────────────────────────────────────────────────

    def _load_models(self):
        """Auto-discover and load .pkl model files from ml/models/."""
        try:
            import joblib
        except ImportError:
            logger.warning('[ModelService] joblib not installed. pip install joblib')
            return

        rain_path   = MODELS_DIR / 'xgb_rainfall.pkl'
        temp_path   = MODELS_DIR / 'xgb_temperature.pkl'
        scaler_path = MODELS_DIR / 'feature_scaler.pkl'
        meta_path   = MODELS_DIR / 'model_meta.json'

        if rain_path.exists() and temp_path.exists():
            try:
                self._rainfall_model    = joblib.load(rain_path)
                self._temperature_model = joblib.load(temp_path)
                if scaler_path.exists():
                    self._scaler = joblib.load(scaler_path)
                    logger.info('[ModelService] Feature scaler loaded.')

                if meta_path.exists():
                    with open(meta_path) as f:
                        self._model_meta = json.load(f)

                self._ready = True
                logger.info(
                    f'[ModelService] ✅ XGBoost models loaded from {MODELS_DIR}. '
                    f'Meta: {self._model_meta}'
                )
                self._write_meta()

            except Exception as e:
                logger.error(f'[ModelService] ❌ Failed to load models: {e}')
                self._ready = False
        else:
            logger.info(
                '[ModelService] ⚠️  No model .pkl files found in ml/models/. '
                'Using IDW spatial fallback. Drop xgb_rainfall.pkl and '
                'xgb_temperature.pkl into ml/models/ when ready.'
            )
            self._ready = False

    def _write_meta(self):
        """Write/update model_meta.json with load timestamp."""
        from datetime import datetime
        meta = {
            'loaded_at': datetime.utcnow().isoformat(),
            'rainfall_model':    'xgb_rainfall.pkl',
            'temperature_model': 'xgb_temperature.pkl',
            'scaler':            'feature_scaler.pkl' if self._scaler else None,
            'schema_version':    '1.0',
        }
        try:
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            with open(MODELS_DIR / 'model_meta.json', 'w') as f:
                json.dump(meta, f, indent=2)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Public Prediction API
    # ─────────────────────────────────────────────────────────────────────────

    def predict_rainfall(self, features: dict) -> float | None:
        """
        Predict 24h rainfall (mm) for a given feature dict.
        Returns None if model not loaded (triggers IDW fallback in views).
        """
        if not self._ready:
            return None
        from ml.ap_feature_schema import RAINFALL_FEATURES
        try:
            X = self._build_vector(features, RAINFALL_FEATURES)
            result = float(self._rainfall_model.predict(X)[0])
            return max(0.0, result)   # rainfall can't be negative
        except Exception as e:
            logger.error(f'[ModelService] Rainfall prediction error: {e}')
            return None

    def predict_temperature(self, features: dict) -> dict | None:
        """
        Predict temperature (°C) for a given feature dict.
        Returns {'tmax_c': float, 'tmin_c': float} or None.
        """
        if not self._ready:
            return None
        from ml.ap_feature_schema import TEMPERATURE_FEATURES
        try:
            X = self._build_vector(features, TEMPERATURE_FEATURES)
            result = self._temperature_model.predict(X)[0]

            # Handle single-output model (Tmax only) or multi-output [Tmax, Tmin]
            if hasattr(result, '__len__') and len(result) >= 2:
                return {'tmax_c': float(result[0]), 'tmin_c': float(result[1])}
            else:
                tmax = float(result)
                return {'tmax_c': tmax, 'tmin_c': tmax - 5.5}  # Tmin estimate

        except Exception as e:
            logger.error(f'[ModelService] Temperature prediction error: {e}')
            return None

    def predict_simulation(self, base_features: dict, deltas: dict) -> dict:
        """
        What-If simulation: apply parameter deltas and re-run prediction.
        
        Args:
            base_features: feature dict for the selected location
            deltas: {
                'temp_delta': float,     # °C shift applied to lag temps
                'rain_delta': float,     # % change applied to lag rainfall
            }
        
        Returns:
            {'rainfall_mm', 'tmax_c', 'tmin_c', 'risk', 'source'}
        """
        modified = {**base_features}

        if 'temp_delta' in deltas and deltas['temp_delta'] != 0:
            d = float(deltas['temp_delta'])
            modified['tmax_lag1'] = modified.get('tmax_lag1', 33.0) + d
            modified['tmin_lag1'] = modified.get('tmin_lag1', 24.0) + d
            modified['tmax_lag2'] = modified.get('tmax_lag2', 33.0) + d
            modified['tmin_lag2'] = modified.get('tmin_lag2', 24.0) + d

        if 'rain_delta' in deltas and deltas['rain_delta'] != 0:
            factor = 1.0 + (float(deltas['rain_delta']) / 100.0)
            for lag in ['rain_lag1', 'rain_lag2', 'rain_lag3']:
                modified[lag] = max(0.0, modified.get(lag, 5.0) * factor)

        rain = self.predict_rainfall(modified)
        temp = self.predict_temperature(modified)

        # If model not ready, use IDW-based fallback estimate
        if rain is None or temp is None:
            from ml.fallback_idw import IDWFallback
            rain, temp, _ = IDWFallback.predict(
                modified.get('lat', 15.9),
                modified.get('lng', 79.7)
            )

        risk = self._compute_risk(rain, temp, modified)

        return {
            'rainfall_mm': rain,
            'tmax_c': temp.get('tmax_c'),
            'tmin_c': temp.get('tmin_c'),
            'risk': risk,
            'source': 'xgboost_simulation' if self._ready else 'idw_simulation',
        }

    def get_status(self) -> dict:
        """Return model loading status (used by /api/model-status/ endpoint)."""
        return {
            'loaded': self._ready,
            'rainfall_model':    (MODELS_DIR / 'xgb_rainfall.pkl').exists(),
            'temperature_model': (MODELS_DIR / 'xgb_temperature.pkl').exists(),
            'scaler':            (MODELS_DIR / 'feature_scaler.pkl').exists(),
            'meta': self._model_meta,
            'models_dir': str(MODELS_DIR),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Internal Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _build_vector(self, features: dict, schema: list) -> 'np.ndarray':
        """
        Construct the numpy feature array from a feature dict,
        using schema order and filling missing values with FEATURE_DEFAULTS.
        """
        from ml.ap_feature_schema import FEATURE_DEFAULTS

        # Compute seasonal encodings if not already present
        month = float(features.get('month', FEATURE_DEFAULTS['month']))
        features.setdefault('month_sin', math.sin(2 * math.pi * month / 12))
        features.setdefault('month_cos', math.cos(2 * math.pi * month / 12))

        vec = [
            float(features.get(f, FEATURE_DEFAULTS.get(f, 0.0)))
            for f in schema
        ]
        X = np.array(vec, dtype=np.float32).reshape(1, -1)

        if self._scaler is not None:
            X = self._scaler.transform(X)

        return X

    @staticmethod
    def _compute_risk(rain: float, temp: dict, features: dict) -> dict:
        """
        Compute drought, flood, and heatwave risk indices
        from predicted rainfall and temperature.
        """
        rain  = rain or 0.0
        tmax  = (temp or {}).get('tmax_c', 33.0)

        # Drought: low rain + high temp
        if   rain < 1.0 and tmax > 38:  drought = 'High'
        elif rain < 3.0 and tmax > 36:  drought = 'Medium'
        else:                             drought = 'Low'

        # Flood: heavy rainfall
        if   rain > 50:   flood = 'High'
        elif rain > 25:   flood = 'Medium'
        else:              flood = 'Low'

        # Heatwave: extreme temperature
        if   tmax > 42:   heatwave = 'Extreme'
        elif tmax > 40:   heatwave = 'High'
        elif tmax > 37:   heatwave = 'Medium'
        else:              heatwave = 'Low'

        # Agriculture impact (simple stress proxy)
        agri = 'Low'
        if drought == 'High' or heatwave in ('High', 'Extreme'):
            agri = 'High'
        elif drought == 'Medium' or heatwave == 'Medium':
            agri = 'Medium'

        return {
            'drought':   drought,
            'flood':     flood,
            'heatwave':  heatwave,
            'agri':      agri,
        }

    @property
    def is_ready(self) -> bool:
        return self._ready
