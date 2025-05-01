#!/usr/bin/env python3
import os
import sys
import unittest

# Add parent directory to path to import server modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the test cases
from tests.test_sqlite_todo_service import TestSQLiteTodoService

if __name__ == "__main__":
    # Create test suite
    loader = unittest.TestLoader()
    
    # Add todo service tests
    suite = loader.loadTestsFromTestCase(TestSQLiteTodoService)
    
    # Create test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run tests
    print("\n======= Running SQLite Todo Service Tests =======")
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(not result.wasSuccessful())
