import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json
import requests
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.weather_service import WeatherService

class TestWeatherService(unittest.TestCase):
    """Test cases for the WeatherService class"""
    
    def setUp(self):
        """Set up test fixtures, if any"""
        # Store original env var
        self.original_api_key = os.environ.get('WEATHER_API_KEY')
        
        # Patch the _verify_api_key method to avoid real API calls during initialization
        with patch.object(WeatherService, '_verify_api_key', return_value=True):
            self.service = WeatherService()
    
    def tearDown(self):
        """Tear down test fixtures, if any"""
        # Restore original env var
        if self.original_api_key:
            os.environ['WEATHER_API_KEY'] = self.original_api_key
        elif 'WEATHER_API_KEY' in os.environ:
            del os.environ['WEATHER_API_KEY']
    
    def test_init_with_api_key(self):
        """Test initialization with API key"""
        # We need to test with a consistent API key regardless of environment
        with patch.dict(os.environ, {'WEATHER_API_KEY': 'test_api_key'}):
            with patch.object(WeatherService, '_verify_api_key', return_value=True) as mock_verify:
                service = WeatherService()
                mock_verify.assert_called_once()
                self.assertEqual(service.api_key, 'test_api_key')
                self.assertEqual(service.api_base_url, 'http://api.weatherapi.com/v1')
                self.assertTrue(isinstance(service.mock_locations, dict))
    
    def test_init_without_api_key(self):
        """Test initialization without API key"""
        # Temporarily remove API key from environment
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(WeatherService, '_verify_api_key', return_value=False) as mock_verify:
                service = WeatherService()
                mock_verify.assert_called_once()
                self.assertIsNone(service.api_key)
    
    @patch('requests.get')
    def test_api_key_verification_success(self, mock_get):
        """Test successful API key verification"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.service._verify_api_key()
        
        # Assert
        self.assertTrue(result)
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_api_key_verification_failure(self, mock_get):
        """Test failed API key verification"""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.service._verify_api_key()
        
        # Assert
        self.assertFalse(result)
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_get_current_weather_api_success(self, mock_get):
        """Test getting current weather via API successfully"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "location": {"name": "Seattle"},
            "current": {
                "condition": {"text": "Cloudy"},
                "temp_c": 15.5,
                "humidity": 70,
                "wind_kph": 10.4
            }
        }
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.service.get_current_weather({"location": "Seattle"})
        
        # Assert
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["location"], "Seattle")
        self.assertEqual(result["weather"]["condition"], "Cloudy")
        self.assertEqual(result["weather"]["temperature"], 15.5)
        self.assertEqual(result["weather"]["humidity"], 70)
        self.assertEqual(result["weather"]["wind_speed"], 10.4)
        self.assertEqual(result["source"], "weatherapi.com")
    
    @patch('requests.get')
    def test_get_current_weather_api_failure(self, mock_get):
        """Test getting current weather with API failure"""
        # Mock failed API response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "message": "No matching location found."
            }
        }
        mock_get.return_value = mock_response
        
        # Call the method with an invalid location
        result = self.service.get_current_weather({"location": "NonExistentPlace"})
        
        # Assert
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["message"])
    
    def test_get_current_weather_mock_data(self):
        """Test getting current weather from mock data"""
        # Set up service without API key
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(WeatherService, '_verify_api_key', return_value=False):
                service = WeatherService()
                # Call the method with a location in mock data
                result = service.get_current_weather({"location": "new york"})
        
                # Assert
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["location"], "New York")
                self.assertIn("condition", result["weather"])
                self.assertIn("temperature", result["weather"])
                self.assertIn("humidity", result["weather"])
                self.assertIn("wind_speed", result["weather"])
                self.assertEqual(result["source"], "mock")
    
    def test_missing_location_parameter(self):
        """Test error handling when location parameter is missing"""
        # Call without location parameter
        result = self.service.get_current_weather({})
        
        # Assert
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Missing required parameter 'location'")
    
    @patch('requests.get')
    def test_get_forecast_api_success(self, mock_get):
        """Test getting forecast via API successfully"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "location": {"name": "Seattle"},
            "forecast": {
                "forecastday": [
                    {
                        "date": "2025-05-01",
                        "day": {
                            "condition": {"text": "Sunny"},
                            "avgtemp_c": 18.5,
                            "avghumidity": 65,
                            "maxwind_kph": 12.7
                        }
                    },
                    {
                        "date": "2025-05-02",
                        "day": {
                            "condition": {"text": "Partly cloudy"},
                            "avgtemp_c": 17.0,
                            "avghumidity": 70,
                            "maxwind_kph": 15.3
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.service.get_forecast({"location": "Seattle", "days": 2})
        
        # Assert
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["location"], "Seattle")
        self.assertEqual(len(result["forecast"]), 2)
        self.assertEqual(result["forecast"][0]["date"], "2025-05-01")
        self.assertEqual(result["forecast"][0]["weather"]["condition"], "Sunny")
        self.assertEqual(result["source"], "weatherapi.com")
    
    def test_get_forecast_mock_data(self):
        """Test getting forecast from mock data"""
        # Set up service without API key
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(WeatherService, '_verify_api_key', return_value=False):
                service = WeatherService()
                # service.api_key should be None from initialization
                
                # Call the method with a location in mock data
                result = service.get_forecast({"location": "london", "days": 3})
                
                # Assert
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["location"], "London")
                self.assertEqual(len(result["forecast"]), 3)
                self.assertEqual(result["source"], "mock")
    
    def test_fallback_to_mock_with_network_error(self):
        """Test fallback to mock data when network error occurs"""
        # Only test this if we have a mock location
        with patch('requests.get') as mock_get:
            # Simulate a network error
            mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
            
            # Call the method with a location in mock data
            result = self.service.get_current_weather({"location": "london"})
            
            # Assert we got mock data as fallback
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["location"], "London")
            self.assertEqual(result["source"], "mock")
    
    def test_non_existent_location_without_api(self):
        """Test error handling for non-existent location without API"""
        # Set up service without API key
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(WeatherService, '_verify_api_key', return_value=False):
                service = WeatherService()
                
                # Call with location not in mock data
                result = service.get_current_weather({"location": "non_existent_place"})
                
                # Assert
                self.assertEqual(result["status"], "error")
                self.assertIn("not found", result["message"])

if __name__ == '__main__':
    unittest.main()
