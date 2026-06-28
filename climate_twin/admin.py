from django.contrib import admin
from .models import ClimateObservation, District

# Registering the models so you can see them in the UI
admin.site.register(District)

@admin.register(ClimateObservation)
class ClimateObservationAdmin(admin.ModelAdmin):
    # This controls which columns you see in the dashboard
    list_display = ('date', 'latitude', 'longitude', 'temperature', 'rainfall', 'sst', 'lst', 'is_ocean')
    list_filter = ('is_ocean', 'date')