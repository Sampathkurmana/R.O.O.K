import os
import sys
import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rook.settings')

# Initialize django if needed (usually model_service.py doesn't strictly require it unless django settings are accessed)
try:
    import django
    django.setup()
except Exception:
    pass

from ml.model_service import ModelService

def main():
    service = ModelService.get_instance()
    print(f"Model Service initialized. Ready state: {service.is_ready}")
    
    locations = [
        ('Visakhapatnam', 17.69, 83.22),
        ('Kurnool',       15.83, 78.04),
        ('Guntur',        16.31, 80.45)
    ]
    
    today = datetime.date.today()
    print(f"\nPredictions for {today}:")
    print(f"  {'Location':<18} {'Latitude':<8} {'Longitude':<10} {'Humidity (%)':<14} {'Temperature':<12} {'Rainfall':<10}")
    print("  " + "-"*70)
    
    for name, lat, lng in locations:
        res = service.predict_all(lat, lng, today)
        print(f"  {name:<18} {lat:<8.2f} {lng:<10.2f} {res['humidity']:<14.2f} {res['temperature']:<12.2f} {res['rainfall']:<10.2f}")

if __name__ == '__main__':
    main()
