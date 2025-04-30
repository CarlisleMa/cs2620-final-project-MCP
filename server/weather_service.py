import json
import time
import random
import os
import logging
import requests
from datetime import datetime, timedelta

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logging.warning("python-dotenv not installed. Environment variables may not be loaded from .env file.")

class WeatherService:
    """Weather service for the distributed system using Weather API"""
    
    def __init__(self):
        # Default API key - in production, use environment variables
        self.api_key = os.environ.get('WEATHER_API_KEY', None)
        self.api_base_url = "http://api.weatherapi.com/v1"
        
        # NOTE: The service works with ANY location through the Weather API!
        # These predefined locations are ONLY used for mock data when the API is unavailable
        # The API supports worldwide locations - no need to add more entries here
        self.mock_locations = {
            "new york": {"lat": 40.7128, "lon": -74.0060},
            "london": {"lat": 51.5074, "lon": -0.1278},
            "tokyo": {"lat": 35.6762, "lon": 139.6503},
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
        
        # Verify API key
        if self._verify_api_key():
            print("✅ Weather API key verified successfully! Real-time weather data is available.")
        else:
            print("⚠️ Weather API key verification failed. Only predefined locations will work with mock data.")
            print("   To use real-time weather data for any location worldwide, please set your API key.")
    
    def _verify_api_key(self):
        """Verify that the API key is registered and working"""
        if not self.api_key:
            logging.warning("⚠️ WEATHER_API_KEY not set. Using mock data only.")
            return False
        
        # Test the API key with a simple request
        try:
            url = f"{self.api_base_url}/current.json"
            params = {
                "key": self.api_key,
                "q": "London",  # Use a major city for the test
                "aqi": "no"
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                print("✅ Weather API key verified successfully! Real-time weather data is available.")
                return True
            else:
                error_msg = "Invalid API key or API request failed"
                if response.status_code == 401 or response.status_code == 403:
                    error_msg = "Invalid or unauthorized API key"
                elif response.status_code == 429:
                    error_msg = "API rate limit exceeded"
                
                logging.error(f"⚠️ Weather API key verification failed: {error_msg} (Status code: {response.status_code})")
                print(f"⚠️ Weather API key verification failed: {error_msg}")
                print("   Falling back to mock data for predefined locations only.")
                return False
        except Exception as e:
            logging.error(f"⚠️ Weather API connection error: {str(e)}")
            print(f"⚠️ Weather API connection error: {str(e)}")
            print("   Check your internet connection. Falling back to mock data for predefined locations.")
            return False
    
    def get_current_weather(self, params, **kwargs):
        """Get current weather for a location"""
        if 'location' not in params:
            return {"error": "Missing required parameter 'location'"}
        
        location = params['location'].lower()
        
        # Try to get real weather data if API key is available
        if self.api_key:
            try:
                weather = self._get_weather_from_api(location)
                return {
                    "status": "success",
                    "location": location.title(),
                    "weather": weather,
                    "timestamp": time.time(),
                    "source": "weatherapi.com"
                }
            except Exception as e:
                logging.error(f"Error fetching weather data: {str(e)}")
                # Check if it's a "location not found" error from the API
                if "not found" in str(e).lower() or "no matching location" in str(e).lower():
                    return {
                        "status": "error",
                        "message": f"Location '{location}' not found"
                    }
                # Fall back to mock data for other errors
        
        # If no API key or we want to use mock data for a known location
        if location in self.mock_locations:
            weather = self._generate_weather_data(location)
            
            return {
                "status": "success",
                "location": location.title(),
                "weather": weather,
                "timestamp": time.time(),
                "source": "mock"
            }
        else:
            # If we get here, either we don't have an API key or the API had an error
            # and the location isn't in our mock data
            return {
                "status": "error",
                "message": f"Location '{location}' not found. Please check the spelling or try a more common location name."
            }
    
    def get_forecast(self, params, **kwargs):
        """Get weather forecast for a location"""
        if 'location' not in params:
            return {"error": "Missing required parameter 'location'"}
        
        location = params['location'].lower()
        days = min(params.get('days', 5), 10)  # Max 10 days
        
        # Try to get real forecast data if API key is available
        if self.api_key:
            try:
                forecast_data = self._get_forecast_from_api(location, days)
                return {
                    "status": "success",
                    "location": location.title(),
                    "forecast": forecast_data,
                    "timestamp": time.time(),
                    "source": "weatherapi.com"
                }
            except Exception as e:
                logging.error(f"Error fetching forecast data: {str(e)}")
                # Check if it's a "location not found" error from the API
                if "not found" in str(e).lower() or "no matching location" in str(e).lower():
                    return {
                        "status": "error",
                        "message": f"Location '{location}' not found"
                    }
                # Continue to try mock data for other errors
        
        # If no API key or we want to use mock data for a known location
        if location in self.mock_locations:
            # Generate mock forecast data as fallback
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
                "timestamp": time.time(),
                "source": "mock"
            }
        else:
            # If we get here, either we don't have an API key or the API had an error
            # and the location isn't in our mock data
            return {
                "status": "error",
                "message": f"Location '{location}' not found. Please check the spelling or try a more common location name."
            }
    
    def _get_weather_from_api(self, location):
        """Get current weather data from Weather API"""
        url = f"{self.api_base_url}/current.json"
        params = {
            "key": self.api_key,
            "q": location,
            "aqi": "no"  # Air quality data not needed
        }
        
        response = requests.get(url, params=params)
        
        # Check for error responses
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", f"API Error: {response.status_code}")
                raise Exception(error_msg)
            except ValueError:
                # If we can't parse the JSON
                raise Exception(f"API Error: {response.status_code}")
        
        data = response.json()
        
        # Map Weather API response to our format
        weather_data = {
            "condition": data["current"]["condition"]["text"],
            "temperature": data["current"]["temp_c"],
            "humidity": data["current"]["humidity"],
            "wind_speed": data["current"]["wind_kph"]
        }
        
        return weather_data
    
    def _get_forecast_from_api(self, location, days):
        """Get forecast data from Weather API"""
        url = f"{self.api_base_url}/forecast.json"
        params = {
            "key": self.api_key,
            "q": location,
            "days": days,
            "aqi": "no"
        }
        
        response = requests.get(url, params=params)
        
        # Check for error responses
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", f"API Error: {response.status_code}")
                raise Exception(error_msg)
            except ValueError:
                # If we can't parse the JSON
                raise Exception(f"API Error: {response.status_code}")
        
        data = response.json()
        forecast = []
        
        for day in data["forecast"]["forecastday"]:
            forecast.append({
                "date": day["date"],
                "weather": {
                    "condition": day["day"]["condition"]["text"],
                    "temperature": day["day"]["avgtemp_c"],
                    "humidity": day["day"]["avghumidity"],
                    "wind_speed": day["day"]["maxwind_kph"]
                }
            })
        
        return forecast
    
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