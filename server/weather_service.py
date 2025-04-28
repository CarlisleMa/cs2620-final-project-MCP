import json
import time
import random
from datetime import datetime, timedelta

class WeatherService:
    """Weather service for the distributed system"""
    
    def __init__(self):
        self.locations = {
            "new york": {"lat": 40.7128, "lon": -74.0060},
            "london": {"lat": 51.5074, "lon": -0.1278},
            "tokyo": {"lat": 35.6762, "lon": -139.6503},
            "paris": {"lat": 48.8566, "lon": 2.3522},
            "sydney": {"lat": -33.8688, "lon": 151.2093},
            "san francisco": {"lat": 37.7749, "lon": -122.4194},
            "boston": {"lat": 42.3601, "lon": -71.0589},
            "chicago": {"lat": 41.8781, "lon": -87.6298},
        }
        
        self.weather_conditions = [
            "Sunny", "Partly Cloudy", "Cloudy", 
            "Rainy", "Thunderstorms", "Snowy", 
            "Foggy", "Clear", "Windy"
        ]
    
    def get_current_weather(self, params, **kwargs):
        """Get current weather for a location"""
        if 'location' not in params:
            return {"error": "Missing required parameter 'location'"}
        
        location = params['location'].lower()
        
        # Check if location exists
        if location not in self.locations:
            return {
                "status": "error",
                "message": f"Location '{location}' not found"
            }
        
        # Simulate API call delay
        time.sleep(random.uniform(0.1, 0.5))
        
        # Generate weather data
        weather = self._generate_weather_data(location)
        
        return {
            "status": "success",
            "location": location.title(),
            "weather": weather,
            "timestamp": time.time()
        }
    
    def get_forecast(self, params, **kwargs):
        """Get weather forecast for a location"""
        if 'location' not in params:
            return {"error": "Missing required parameter 'location'"}
        
        location = params['location'].lower()
        days = min(params.get('days', 5), 10)  # Max 10 days
        
        # Check if location exists
        if location not in self.locations:
            return {
                "status": "error",
                "message": f"Location '{location}' not found"
            }
        
        # Simulate API call delay
        time.sleep(random.uniform(0.2, 0.7))
        
        # Generate forecast data
        forecast = []
        current_date = datetime.now()
        
        for i in range(days):
            forecast_date = current_date + timedelta(days=i)
            forecast.append({
                "date": forecast_date.strftime("%Y-%m-%d"),
                "weather": self._generate_weather_data(location, forecast_date),
            })
        
        return {
            "status": "success",
            "location": location.title(),
            "forecast": forecast,
            "timestamp": time.time()
        }
    
    def _generate_weather_data(self, location, date=None):
        """Generate random but consistent weather data for a location"""
        if date is None:
            date = datetime.now()
        
        # Use location and date to seed the random generator for consistency
        seed = f"{location}:{date.strftime('%Y-%m-%d')}"
        random.seed(hash(seed))
        
        # Generate temperature based on location and season
        base_temp = 20  # Base temperature in Celsius
        
        # Adjust for location
        if "london" in location or "paris" in location:
            base_temp -= 5
        elif "tokyo" in location:
            base_temp += 3
        elif "sydney" in location:
            base_temp += 5
        elif "boston" in location:
            base_temp += 10
        elif "chicago" in location or "new york" in location:
            base_temp -= 3
        
        # Adjust for season (northern hemisphere)
        month = date.month
        if month in [12, 1, 2]:  # Winter
            base_temp -= 15
        elif month in [3, 4, 5]:  # Spring
            base_temp -= 5
        elif month in [6, 7, 8]:  # Summer
            base_temp += 10
        else:  # Fall
            base_temp += 0
        
        # Randomize a bit
        temp = base_temp + random.uniform(-5, 5)
        
        # Select weather condition
        condition = random.choice(self.weather_conditions)
        
        # Generate humidity
        humidity = random.randint(30, 90)
        
        # Generate wind speed
        wind_speed = random.uniform(0, 30)
        
        return {
            "condition": condition,
            "temperature": round(temp, 1),
            "humidity": humidity,
            "wind_speed": round(wind_speed, 1)
        }