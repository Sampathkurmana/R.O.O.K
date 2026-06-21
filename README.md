# R.O.O.K - Resilient Observation & Outlook Kernel
### AI-Powered Climate Digital Twin Platform of India (Pilot Andhra Pradesh)

ROOK is a high-fidelity geospatial climate digital twin web application, featuring real-time observations, predictive weather charts, satellite layer overlays, severe warning alerts, and an interactive climate simulator engine.

Developed for Django, Python, PostgreSQL/MySQL (with SQLite default fallback), Leaflet.js, and ApexCharts.

---

## Technical Stack
- **Backend:** Python 3.x, Django, Django REST Framework (DRF)
- **AI/Simulation Layer:** NumPy, Scikit-Learn (Random Forest & Multi-variable Regressions)
- **Frontend:** HTML5, CSS3, TailwindCSS, ApexCharts, Lucide Icons, GSAP
- **Geospatial Mapping:** Leaflet.js with CARTO Dark Matter Tiles & Custom Vector Overlays

---

## Directory Structure
```text
ROOK/
├── climate_twin/               # Main Django application
│   ├── api/                    # REST framework endpoints
│   │   ├── __init__.py
│   │   └── views.py            # Weather, forecast, digital twin APIs
│   ├── services/
│   │   └── ai_service.py       # AI model predictions & mathematical simulators
│   ├── __init__.py
│   ├── settings.py             # Project configurations & DB fallbacks
│   ├── urls.py                 # Core routing
│   ├── views.py                # Dashboard templates router
│   ├── models.py               # ORM Database Models
│   ├── wsgi.py
│   └── asgi.py
├── templates/
│   ├── base.html               # Shared HTML shell (scripts/styles loader)
│   └── index.html              # Dynamic dashboard, widgets and panels
├── static/
│   ├── css/
│   │   └── custom.css          # Glassmorphic classes, keyframe animations
│   └── js/
│   │     └── app.js            # Leaflet logic, map redraw events, charts
├── manage.py                   # Django manager script
├── populate_db.py              # Pre-population seeding script
└── README.md                   # This instruction sheet
```

---

## Setup & Running Guide

### 1. Prerequisites
Install all the required Python packages:
```bash
pip install django djangorestframework django-cors-headers numpy scikit-learn
```

### 2. Database Migrations
Create your database schema using Django's ORM:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Database Seeding
Run the seed script to populate historical records, warning alerts, and forecast data for the 13 district stations of Andhra Pradesh:
```bash
python populate_db.py
```

### 4. Fire up the Server
Start the local development server:
```bash
python manage.py runserver
```

Open your browser and navigate to:
**[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## Features Walkthrough
1. **Live Weather & Map Pinpoints:** Click on any of the 13 district stations markers on the map to query local conditions. The floating dashboard cards update instantly with fluid micro-animations.
2. **5-Day Climatology Trends:** Charts dynamically update showing forecast curves using historical trend regressions.
3. **Digital Twin Timeline Interpolation:** Slide the timeline bar at the bottom right between **Past (-5Y)**, **Present**, and **Future (+10Y)**. Spatial layers (Rainfall, Temp, Humidity, LST, SST) dynamically recalculate and overlay onto the map.
4. **Scenario Simulator Engine:** Drag the deviations sliders (Temperature, Rain, and Humidity) to simulate severe anomalies. The simulator calculates Drought, Heatwave, and Flood risks immediately, adjusting the map polygon fill to represent hazards.
5. **Data Feeds Status:** Monitor status indicators showing connection status with space research entities (ISRO Bhuvan, IMD AWS, MOSDAC).
