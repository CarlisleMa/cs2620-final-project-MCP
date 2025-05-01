import unittest
import sys
import os
import time
import uuid
import tempfile
import sqlite3
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path to import server modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.sqlite_todo_service import SQLiteTodoService
from server.db_manager import DatabaseManager


class TestSQLiteTodoService(unittest.TestCase):
    """Test cases for the SQLite-based Todo service"""

    def setUp(self):
        """Set up a test environment with a temporary database"""
        # Create a temp file for the test database
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db_file.close()
        
        # Create a database manager with the temp file
        self.db_manager = DatabaseManager(self.temp_db_file.name)
        
        # Create the todo service with the test database
        self.todo_service = SQLiteTodoService(self.temp_db_file.name)
        
        # Create a test client ID
        self.test_client_id = f"test_client_{uuid.uuid4().hex[:8]}"
        
        print(f"Test database created at: {self.temp_db_file.name}")
    
    def tearDown(self):
        """Clean up the test database"""
        # Close database connections
        if hasattr(self, 'db_manager'):
            self.db_manager.close_all()
        
        # Remove the temp database file
        if hasattr(self, 'temp_db_file') and os.path.exists(self.temp_db_file.name):
            os.remove(self.temp_db_file.name)
            print(f"Test database removed: {self.temp_db_file.name}")
    
    def test_add_task_basic(self):
        """Test adding a basic task with minimal information"""
        task_params = {
            "title": "Test Task"
        }
        
        # Add the task
        result = self.todo_service.add_task(task_params, client_id=self.test_client_id)
        
        # Check the result
        self.assertEqual(result["status"], "success")
        self.assertIn("task_id", result)
        self.assertTrue(result["task_id"])  # Ensure task_id is not empty
    
    def test_add_task_with_all_fields(self):
        """Test adding a task with all fields populated"""
        task_params = {
            "title": "Complete Task",
            "description": "This is a test task with all fields",
            "due_date": "2025-12-31",
            "priority": "high"
        }
        
        # Add the task
        result = self.todo_service.add_task(task_params, client_id=self.test_client_id)
        
        # Check the result
        self.assertEqual(result["status"], "success")
        self.assertIn("task_id", result)
        
        # Verify the task can be retrieved
        task_id = result["task_id"]
        conn = sqlite3.connect(self.temp_db_file.name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        conn.close()
        
        self.assertEqual(task["title"], "Complete Task")
        self.assertEqual(task["description"], "This is a test task with all fields")
        self.assertEqual(task["due_date"], "2025-12-31")
        self.assertEqual(task["priority"], "high")
    
    def test_add_task_missing_title(self):
        """Test adding a task without a title (should fail)"""
        task_params = {
            "description": "Task with no title"
        }
        
        # Add the task
        result = self.todo_service.add_task(task_params, client_id=self.test_client_id)
        
        # Check the result (should contain an error)
        self.assertIn("error", result)
    
    def test_add_and_get_task(self):
        """Test adding a task and then retrieving it"""
        # Add a task
        task_params = {
            "title": "Task to Retrieve",
            "priority": "medium",
            "due_date": "2025-05-15"
        }
        
        add_result = self.todo_service.add_task(task_params, client_id=self.test_client_id)
        self.assertEqual(add_result["status"], "success")
        
        # Get tasks for the client
        get_params = {"include_completed": False}
        get_result = self.todo_service.get_tasks(get_params, client_id=self.test_client_id)
        
        # Check the result
        self.assertEqual(get_result["status"], "success")
        self.assertIn("tasks", get_result)
        self.assertTrue(len(get_result["tasks"]) > 0)
        
        # Check if our task is in the results
        found_task = False
        for task in get_result["tasks"]:
            if task["title"] == "Task to Retrieve":
                found_task = True
                self.assertEqual(task["priority"], "medium")
                self.assertEqual(task["due_date"], "2025-05-15")
                break
        
        self.assertTrue(found_task, "Added task was not found in get_tasks results")
    
    def test_add_multiple_tasks(self):
        """Test adding multiple tasks and retrieving them all"""
        # Add several tasks
        task_titles = ["Task 1", "Task 2", "Task 3", "Task 4", "Task 5"]
        
        for title in task_titles:
            params = {"title": title}
            result = self.todo_service.add_task(params, client_id=self.test_client_id)
            self.assertEqual(result["status"], "success")
        
        # Get all tasks
        get_result = self.todo_service.get_tasks({}, client_id=self.test_client_id)
        
        # Check if all tasks were retrieved
        self.assertEqual(get_result["status"], "success")
        self.assertEqual(len(get_result["tasks"]), 5)
        
        # Check if all titles are present
        retrieved_titles = [task["title"] for task in get_result["tasks"]]
        for title in task_titles:
            self.assertIn(title, retrieved_titles)
    
    def test_task_persistence(self):
        """Test that tasks are persisted in the database"""
        # Add a task
        task_params = {"title": "Persistent Task"}
        add_result = self.todo_service.add_task(task_params, client_id=self.test_client_id)
        self.assertEqual(add_result["status"], "success")
        
        # Create a new service instance with the same database
        new_service = SQLiteTodoService(self.temp_db_file.name)
        
        # Get tasks from the new service
        get_result = new_service.get_tasks({}, client_id=self.test_client_id)
        
        # Check if our task was persisted
        self.assertTrue(any(task["title"] == "Persistent Task" for task in get_result["tasks"]))


if __name__ == "__main__":
    unittest.main()
