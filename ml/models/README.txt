# This directory is where you drop your trained XGBoost model files.
#
# Required files:
#   xgb_rainfall.pkl        — Trained XGBoost rainfall regressor
#   xgb_temperature.pkl     — Trained XGBoost temperature regressor
#
# Optional:
#   feature_scaler.pkl      — StandardScaler if you scaled features during training
#
# After dropping files here:
#   1. Run: python ml/validate_model.py
#   2. Restart: python manage.py runserver
#   → Real predictions go live automatically
