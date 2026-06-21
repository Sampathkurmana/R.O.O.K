from django.db import models

class ClimateObservation(models.Model):
    """
    Stores historical and real-time physical observations at specific coordinates.
    """
    date = models.DateField(db_index=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    rainfall = models.FloatField(help_text="Rainfall in mm")
    temperature = models.FloatField(help_text="Air temperature in Celsius")
    humidity = models.FloatField(help_text="Relative humidity percentage")
    lst = models.FloatField(help_text="Land Surface Temperature in Celsius")
    sst = models.FloatField(help_text="Sea Surface Temperature in Celsius")
    wind_speed = models.FloatField(default=0.0, help_text="Wind speed in knots")
    wind_direction = models.CharField(max_length=8, default="N", help_text="Wind direction vector")

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"Observation {self.date} at ({self.latitude}, {self.longitude})"


class ClimatePrediction(models.Model):
    """
    Stores AI/ML model generated predictions for future weather trends.
    """
    date = models.DateField(unique=True, db_index=True)
    rainfall_prediction = models.FloatField(help_text="Predicted rainfall in mm")
    temperature_prediction = models.FloatField(help_text="Predicted temperature in Celsius")
    humidity_prediction = models.FloatField(default=60.0, help_text="Predicted humidity percentage")
    wind_speed_prediction = models.FloatField(default=10.0, help_text="Predicted wind speed in knots")

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"Prediction for {self.date}"


class ScenarioSimulation(models.Model):
    """
    Saves simulation scenario adjustments and their computed hazards.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    rainfall_change = models.FloatField(help_text="Percentage rainfall change (-50 to +50)")
    temperature_change = models.FloatField(help_text="Temperature delta in Celsius (-5 to +5)")
    humidity_change = models.FloatField(help_text="Humidity delta in percentage points (-20 to +20)")
    
    # Calculated risk outputs (0.0 to 1.0 or text levels)
    drought_risk = models.CharField(max_length=16, help_text="Low/Medium/High/Critical")
    flood_risk = models.CharField(max_length=16, help_text="Low/Medium/High/Critical")
    heatwave_risk = models.CharField(max_length=16, help_text="Low/Medium/High/Critical")
    agricultural_impact = models.CharField(max_length=32, help_text="Risk status description")
    water_stress_index = models.FloatField(help_text="Calculated stress coefficient (0.0 to 100.0)")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Simulation T:{self.temperature_change:+}C, R:{self.rainfall_change:+}%"


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
