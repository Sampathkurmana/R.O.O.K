import pandas as pd
import xgboost as xgb
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib

# 1. Load the dataset dynamically relative to this script
dataset_path = Path(__file__).resolve().parent / "datasets" / "dataset.csv"
df = pd.read_csv(dataset_path)

# 2. Clean up: Drop rows where we don't even know the target wind speed
df = df.dropna(subset=['WindSpeed'])

# 3. Stop the cheating: Drop U/V vectors and non-numeric columns
X = df.drop(columns=['Date', 'Wind_U_m_s', 'Wind_V_m_s', 'WindSpeed'])
y = df['WindSpeed']

# 4. Split it up (80% for studying, 20% for the final exam)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 5. Build the XGBoost Brain 🧠
model = xgb.XGBRegressor(
    n_estimators=150,     # How many decision trees to build
    learning_rate=0.1,    # How fast it learns (don't make it too fast or it gets dumb)
    max_depth=7,          # How deep the trees go
    random_state=42,
    enable_categorical=False 
)

# 6. Train it
print("Training the XGBoost model... hold your horses 🐎")
model.fit(X_train, y_train)

# 7. Test it
preds = model.predict(X_test)
import numpy as np
mse = mean_squared_error(y_test, preds)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, preds)

print(f"Wind Prediction RMSE: {rmse:.2f} m/s")
print(f"R² Score: {r2:.2f} (closer to 1.0 is better!)")

model_path = Path(__file__).resolve().parent / "models" / "xgb_windspeed.pkl"
model_path.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(model, model_path)
print(f"✅ Wind model saved to {model_path}")