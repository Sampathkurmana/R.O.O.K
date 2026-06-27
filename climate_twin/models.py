from django.db import models

class State(models.Model):
    """
    Administrative state (e.g. Andhra Pradesh)
    """
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name


class District(models.Model):
    """
    District under a State with geographical centroid coordinates.
    """
    name = models.CharField(max_length=64)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="districts")
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        unique_together = ('name', 'state')

    def __str__(self):
        return f"{self.name}, {self.state.name}"


class ClimateObservation(models.Model):
    """
    Stores historical and real-time physical observations at specific coordinates / districts.
    """
    date = models.DateField(db_index=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="observations", null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    rainfall = models.FloatField(help_text="Rainfall in mm")
    temperature = models.FloatField(help_text="Air temperature in Celsius")
    humidity = models.FloatField(help_text="Relative humidity percentage")
    pressure = models.FloatField(default=1008.0, help_text="Atmospheric pressure in hPa")
    wind = models.FloatField(default=14.0, help_text="Wind speed in knots")
    lst = models.FloatField(help_text="Land Surface Temperature in Celsius")
    sst = models.FloatField(help_text="Sea Surface Temperature in Celsius")

    # Kept for backward compatibility with existing usages
    wind_speed = models.FloatField(default=0.0, help_text="Wind speed in knots (alias)")
    wind_direction = models.CharField(max_length=8, default="N", help_text="Wind direction vector")

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
        ]

    def save(self, *args, **kwargs):
        if not self.wind_speed:
            self.wind_speed = self.wind
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Observation {self.date} at ({self.latitude}, {self.longitude})"


class ClimatePrediction(models.Model):
    """
    Stores AI/ML model generated predictions for future weather trends.
    """
    date = models.DateField(db_index=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="predictions", null=True, blank=True)
    latitude = models.FloatField(default=15.9)
    longitude = models.FloatField(default=79.7)
    rainfall = models.FloatField(help_text="Predicted rainfall in mm")
    temperature = models.FloatField(help_text="Predicted temperature in Celsius")
    humidity = models.FloatField(default=60.0, help_text="Predicted humidity percentage")
    pressure = models.FloatField(default=1008.0, help_text="Predicted atmospheric pressure in hPa")
    wind = models.FloatField(default=10.0, help_text="Predicted wind speed in knots")
    lst = models.FloatField(default=35.0, help_text="Predicted Land Surface Temp in Celsius")
    sst = models.FloatField(default=0.0, help_text="Predicted Sea Surface Temp in Celsius")
    prediction_confidence = models.FloatField(default=0.85, help_text="Model prediction confidence score (0.0 to 1.0)")
    horizon = models.CharField(max_length=16, default="1-day", help_text="Forecast horizon: 1-day, 3-day, 7-day")

    # Kept for backward compatibility with existing usages
    rainfall_prediction = models.FloatField(default=0.0, help_text="Predicted rainfall in mm")
    temperature_prediction = models.FloatField(default=0.0, help_text="Predicted temperature in Celsius")
    humidity_prediction = models.FloatField(default=60.0, help_text="Predicted humidity percentage")
    wind_speed_prediction = models.FloatField(default=10.0, help_text="Predicted wind speed in knots")

    class Meta:
        ordering = ['date']

    def save(self, *args, **kwargs):
        if not self.rainfall_prediction:
            self.rainfall_prediction = self.rainfall
        if not self.temperature_prediction:
            self.temperature_prediction = self.temperature
        if not self.wind_speed_prediction:
            self.wind_speed_prediction = self.wind
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Prediction for {self.date} (Horizon: {self.horizon})"


class ClimateSimulation(models.Model):
    """
    Saves simulation scenario adjustments and their computed hazards.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    scenario_category = models.CharField(max_length=32, default="Custom", help_text="Scenario category name")
    temp_change = models.FloatField(default=0.0, help_text="Temperature delta in Celsius")
    rainfall_change = models.FloatField(default=0.0, help_text="Percentage rainfall change")
    humidity_change = models.FloatField(default=0.0, help_text="Humidity delta in percentage points")
    wind_change = models.FloatField(default=0.0, help_text="Wind delta in knots")
    pressure_change = models.FloatField(default=0.0, help_text="Pressure delta in hPa")
    sst_change = models.FloatField(default=0.0, help_text="SST delta in Celsius")
    lst_change = models.FloatField(default=0.0, help_text="LST delta in Celsius")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Simulation run at {self.created_at} - Category: {self.scenario_category}"


class ScenarioSimulation(models.Model):
    """
    Legacy simulation model kept for backward compatibility.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    rainfall_change = models.FloatField(help_text="Percentage rainfall change (-50 to +50)")
    temperature_change = models.FloatField(help_text="Temperature delta in Celsius (-5 to +5)")
    humidity_change = models.FloatField(help_text="Humidity delta in percentage points (-20 to +20)")
    
    drought_risk = models.CharField(max_length=16, help_text="Low/Medium/High/Critical")
    flood_risk = models.CharField(max_length=16, help_text="Low/Medium/High/Critical")
    heatwave_risk = models.CharField(max_length=16, help_text="Low/Medium/High/Critical")
    agricultural_impact = models.CharField(max_length=32, help_text="Risk status description")
    water_stress_index = models.FloatField(help_text="Calculated stress coefficient (0.0 to 100.0)")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Legacy Sim T:{self.temperature_change:+}C, R:{self.rainfall_change:+}%"


class ClimatePlayback(models.Model):
    """
    Logs climate playback state configuration and runs.
    """
    timestamp = models.DateTimeField(auto_now_add=True)
    date_range_start = models.DateField()
    date_range_end = models.DateField()
    speed = models.IntegerField(default=1)
    status = models.CharField(max_length=16, default="active")  # playing, paused, stopped

    def __str__(self):
        return f"Playback session {self.id} ({self.status}) from {self.date_range_start} to {self.date_range_end}"


class RiskAssessment(models.Model):
    """
    Calculated risks for the digital twin state.
    """
    timestamp = models.DateTimeField(auto_now_add=True)
    observation = models.ForeignKey(ClimateObservation, on_delete=models.CASCADE, null=True, blank=True, related_name="risks")
    prediction = models.ForeignKey(ClimatePrediction, on_delete=models.CASCADE, null=True, blank=True, related_name="risks")
    simulation = models.ForeignKey(ClimateSimulation, on_delete=models.CASCADE, null=True, blank=True, related_name="risks")
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, related_name="risks")
    
    heatwave_risk = models.CharField(max_length=16, help_text="Low/Medium/High/Critical")
    flood_risk = models.CharField(max_length=16, help_text="Low/Medium/High/Critical")
    drought_risk = models.CharField(max_length=16, help_text="Low/Medium/High/Critical")
    cyclone_risk = models.CharField(max_length=16, help_text="Low/Medium/High/Critical")
    agriculture_risk = models.CharField(max_length=16, help_text="Low/Medium/High/Critical")
    water_stress = models.FloatField(help_text="Falkenmark index or calculated stress index (0.0 to 100.0)")
    crop_stress = models.FloatField(help_text="Calculated crop stress (0.0 to 100.0)")
    attribution_insights = models.JSONField(default=dict, help_text="Feature importance and insight attribution from models")

    def __str__(self):
        return f"Risk Assessment {self.id} at {self.timestamp}"


class Alert(models.Model):
    """
    Climate warnings generated based on observations and forecasts.
    """
    SEVERITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]

    ALERT_TYPES = [
        ('Heatwave', 'Heatwave'),
        ('Flood', 'Flood'),
        ('Cyclone', 'Cyclone'),
        ('Rainfall', 'Rainfall'),
        ('Drought', 'Drought'),
    ]

    type = models.CharField(max_length=16, choices=ALERT_TYPES)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES)
    district = models.CharField(max_length=64, default="All districts")
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity}] {self.type} - {self.district}"
