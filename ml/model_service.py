"""
ml/model_service.py
====================
Plug-and-Play XGBoost Model Service for R.O.O.K.

This service loads all trained models from ml/models/ and makes unified predictions.
"""

import os
import math
import json
import logging
from pathlib import Path
import datetime

import numpy as np
import pandas as pd
import joblib

logger = logging.getLogger('rook.ml')

MODELS_DIR = Path(__file__).parent / 'models'

class ModelService:
    """
    Singleton that loads XGBoost models once and serves predictions.
    """
    _instance = None
    _models = {}
    _ready = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_models()
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    def _load_models(self):
        """Auto-discover and load .pkl model files from ml/models/."""
        try:
            targets = ['rainfall', 'temperature', 'humidity', 'surface_pressure_hpa', 'windspeed', 'sst', 'lst']
            loaded_count = 0
            for t in targets:
                path = MODELS_DIR / f'xgb_{t}.pkl'
                if path.exists():
                    try:
                        self._models[t] = joblib.load(path)
                        loaded_count += 1
                    except Exception as ex:
                        logger.error(f"[ModelService] Failed to load model for {t}: {ex}")
            
            if loaded_count > 0:
                self._ready = True
                logger.info(f"[ModelService] Loaded {loaded_count} XGBoost models from {MODELS_DIR}")
            else:
                self._ready = False
                logger.warning("[ModelService] No model files found. Using IDW fallback.")
        except Exception as e:
            logger.error(f"[ModelService] Failed to load models: {e}")
            self._ready = False

    def _build_features(self, lat: float, lng: float, date_val: datetime.date) -> pd.DataFrame:
        day_of_year = date_val.timetuple().tm_yday
        is_ocean = 1 if lng > 83.2 else 0
        month = date_val.month
        month_sin = math.sin(2 * math.pi * month / 12)
        month_cos = math.cos(2 * math.pi * month / 12)
        
        row = {
            'Latitude': lat,
            'Longitude': lng,
            'DayOfYear': day_of_year,
            'Is_Ocean': is_ocean,
            'month_sin': month_sin,
            'month_cos': month_cos
        }
        return pd.DataFrame([row])

    def predict_all(self, lat: float, lng: float, date_val: datetime.date) -> dict:
        """
        Predicts all variables using loaded XGBoost models. Falls back to default values if not loaded.
        """
        # Default fallback values from IDW or climatology
        res = {
            'temperature': 32.4,
            'rainfall': 5.0,
            'humidity': 70.0,
            'pressure': 1009.0,
            'wind': 12.0,
            'lst': 34.0,
            'sst': 28.0,
        }
        
        if not self._ready:
            return res

        df_feat = self._build_features(lat, lng, date_val)
        
        for k in res.keys():
            model_key = 'windspeed' if k == 'wind' else ('surface_pressure_hpa' if k == 'pressure' else k)
            model = self._models.get(model_key)
            if model:
                try:
                    pred_val = float(model.predict(df_feat)[0])
                    if k == 'rainfall':
                        pred_val = max(0.0, pred_val)
                    elif k == 'humidity':
                        pred_val = max(0.0, min(100.0, pred_val))
                    res[k] = round(pred_val, 2)
                except Exception as ex:
                    logger.error(f"[ModelService] Failed prediction for {k}: {ex}")
                    
        return res

    def predict_windspeed(self, features: dict) -> float:
        lat = features.get('lat', 15.9)
        lng = features.get('lng', 79.7)
        date_val = datetime.date.today()
        preds = self.predict_all(lat, lng, date_val)
        return preds['wind']

    def predict_rainfall(self, features: dict) -> float | None:
        if not self._ready:
            return None
        lat = features.get('lat', 15.9)
        lng = features.get('lng', 79.7)
        date_val = datetime.date.today()
        preds = self.predict_all(lat, lng, date_val)
        return preds['rainfall']

    def predict_temperature(self, features: dict) -> dict | None:
        if not self._ready:
            return None
        lat = features.get('lat', 15.9)
        lng = features.get('lng', 79.7)
        date_val = datetime.date.today()
        preds = self.predict_all(lat, lng, date_val)
        tmax = preds['temperature']
        return {'tmax_c': tmax, 'tmin_c': round(tmax - 5.5, 1)}

    def predict_simulation(self, base_features: dict, deltas: dict) -> dict:
        """
        Runs what-if simulation by shifting base inputs.
        """
        lat = base_features.get('lat', 15.9)
        lng = base_features.get('lng', 79.7)
        date_val = datetime.date.today()
        
        # Get baseline prediction
        baseline = self.predict_all(lat, lng, date_val)
        
        # Apply deltas to baseline values to get perturbed state
        temp_delta = float(deltas.get('temp_delta', 0.0))
        rain_delta = float(deltas.get('rain_delta', 0.0))
        humidity_change = float(deltas.get('humidity_change', 0.0))
        wind_change = float(deltas.get('wind_change', 0.0))
        pressure_change = float(deltas.get('pressure_change', 0.0))
        
        simulated = {
            'temperature': round(baseline['temperature'] + temp_delta, 2),
            'rainfall': round(max(0.0, baseline['rainfall'] * (1.0 + rain_delta / 100.0)), 2) if rain_delta != 0 else baseline['rainfall'],
            'humidity': round(max(0.0, min(100.0, baseline['humidity'] + humidity_change)), 2),
            'wind': round(max(0.0, baseline['wind'] + wind_change), 2),
            'pressure': round(baseline['pressure'] + pressure_change, 2),
            'lst': round(baseline['lst'] + temp_delta, 2),
            'sst': round(baseline['sst'] + temp_delta, 2) if baseline['sst'] > 0 else 0.0,
        }
        
        # Calculate risks
        from climate_twin.services.core_engines import AnalyticsRiskEngine
        risks = AnalyticsRiskEngine.calculate_risks({
            "temperature": simulated["temperature"],
            "rainfall": simulated["rainfall"],
            "humidity": simulated["humidity"],
            "pressure": simulated["pressure"],
            "wind": simulated["wind"],
            "lst": simulated["lst"],
            "sst": simulated["sst"],
            "temp_change": temp_delta,
            "rainfall_change": rain_delta,
            "humidity_change": humidity_change
        })
        
        return {
            'rainfall_mm': simulated['rainfall'],
            'tmax_c': simulated['temperature'],
            'tmin_c': round(simulated['temperature'] - 5.5, 1),
            'risk': {
                'drought': risks["drought_risk"],
                'flood': risks["flood_risk"],
                'heatwave': risks["heatwave_risk"],
                'agri': risks["agriculture_risk"]
            },
            'source': 'xgboost_simulation' if self._ready else 'idw_simulation'
        }

    def get_status(self) -> dict:
        return {
            'loaded': self._ready,
            'rainfall_model': 'rainfall' in self._models,
            'temperature_model': 'temperature' in self._models,
            'humidity_model': 'humidity' in self._models,
            'pressure_model': 'surface_pressure_hpa' in self._models,
            'windspeed_model': 'windspeed' in self._models,
            'sst_model': 'sst' in self._models,
            'lst_model': 'lst' in self._models,
            'meta': {
                'models_directory': str(MODELS_DIR),
                'feature_names': ['Latitude', 'Longitude', 'DayOfYear', 'Is_Ocean', 'month_sin', 'month_cos']
            }
        }

    @property
    def is_ready(self) -> bool:
        return self._ready
