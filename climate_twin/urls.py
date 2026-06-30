from django.contrib import admin
from django.urls import path, include
from climate_twin import views
from climate_twin.api import views as api_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Frontend Page Routes (each maps to the master map-centric interface with active panel context)
    path('', views.index, name='dashboard'),
    path('weather/', views.index, {'panel': 'weather'}, name='weather'),
    path('forecast/', views.index, {'panel': 'forecast'}, name='forecast'),
    path('analytics/', views.index, {'panel': 'analytics'}, name='analytics'),
    path('climate-intel/', views.index, {'panel': 'climate-intel'}, name='climate_intel'),
    path('digital-twin/', views.index, {'panel': 'digital-twin'}, name='digital_twin'),
    path('simulator/', views.index, {'panel': 'simulator'}, name='simulator'),
    path('satellite/', views.index, {'panel': 'satellite'}, name='satellite'),
    path('alerts/', views.index, {'panel': 'alerts'}, name='alerts'),
    path('reports/', views.index, {'panel': 'reports'}, name='reports'),
    path('sources/', views.index, {'panel': 'sources'}, name='sources'),
    path('settings/', views.index, {'panel': 'settings'}, name='settings'),
    
    # DRF API Routes
    path('api/weather/', api_views.WeatherAPIView.as_view(), name='api_weather'),
    path('api/current/', api_views.WeatherAPIView.as_view(), name='api_current'),
    path('api/history/', api_views.HistoryAPIView.as_view(), name='api_history'),
    path('api/forecast/', api_views.ForecastAPIView.as_view(), name='api_forecast'),
    path('api/digital-twin/', api_views.DigitalTwinAPIView.as_view(), name='api_digital_twin'),
    path('api/simulator/', api_views.SimulatorAPIView.as_view(), name='api_simulator'),
    path('api/simulate/', api_views.SimulateView.as_view(), name='api_simulate_clean'),
    path('api/playback/', api_views.PlaybackAPIView.as_view(), name='api_playback'),
    path('api/alerts/', api_views.AlertsAPIView.as_view(), name='api_alerts'),
    path('api/reports/', api_views.ReportsAPIView.as_view(), name='api_reports'),

    # XGBoost Model-Powered Prediction API (Phase 2)
    path('api/predict/', api_views.PredictView.as_view(), name='api_predict'),
    path('api/predict-simulate/', api_views.SimulateView.as_view(), name='api_simulate'),
    path('api/risk/', api_views.RiskView.as_view(), name='api_risk'),
    path('api/model-status/', api_views.ModelStatusView.as_view(), name='api_model_status'),

    # ─── Climate Intelligence Center API Layer ───────────────────────────────
    path('api/climate/snapshot/', api_views.ClimateSnapshotView.as_view(), name='api_climate_snapshot'),
    path('api/climate/trends/', api_views.ClimateTrendsView.as_view(), name='api_climate_trends'),
    path('api/climate/anomalies/', api_views.ClimateAnomalyView.as_view(), name='api_climate_anomalies'),
    path('api/climate/insights/', api_views.ClimateInsightsView.as_view(), name='api_climate_insights'),
    path('api/climate/comparison/', api_views.ClimateComparisonView.as_view(), name='api_climate_comparison'),
    path('api/climate/story/', api_views.ClimateStoryView.as_view(), name='api_climate_story'),
    path('api/climate/twin-status/', api_views.DigitalTwinStatusView.as_view(), name='api_climate_twin_status'),
]



