#!/usr/bin/env python3
"""
Test runner for Weather Service tests
Run this script to execute all tests for the Weather Service
"""

import unittest
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    # Import the test module
    from tests.test_weather_service import TestWeatherService
    
    # Create a test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestWeatherService)
    
    # Run the tests
    print("======================================================")
    print("🧪 Running Weather Service API Tests")
    print("======================================================")
    
    # Check if API key is set
    api_key = os.environ.get('WEATHER_API_KEY')
    if api_key:
        print(f"✅ Found Weather API key: {api_key[:4]}...{api_key[-4:]}")
    else:
        print("⚠️ No Weather API key found in environment variables.")
        print("   Tests will run with mock API responses only.")
    
    print("\nRunning tests...\n")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n======================================================")
    print(f"Test Summary: {result.testsRun} tests run")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    if result.failures:
        print(f"❌ Failed: {len(result.failures)}")
    if result.errors:
        print(f"⚠️ Errors: {len(result.errors)}")
    print("======================================================")
    
    # Exit with proper code
    sys.exit(not result.wasSuccessful())
