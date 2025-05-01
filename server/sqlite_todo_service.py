import json
import time
import uuid
import logging
import sqlite3
from datetime import datetime
from server.db_manager import DatabaseManager

class SQLiteTodoService:
    """Todo list service that uses SQLite storage for persistence"""
    
    def __init__(self, db_path=None):
        """Initialize the Todo service with SQLite backend
        
        Args:
            db_path: Path to the SQLite database file. If None, a default path will be used.
        """
        self.db_manager = DatabaseManager(db_path)
        logging.info("SQLite Todo Service initialized")
    
    def add_task(self, params, **kwargs):
        """Add a task to a user's todo list
        
        Args:
            params: Dictionary with task details (title, description, due_date, priority)
            kwargs: Additional parameters including client_id
            
        Returns:
            Dictionary with status, message and task_id
        """
        if 'title' not in params:
            return {"error": "Missing required parameter 'title'"}
        
        client_id = kwargs.get('client_id', 'anonymous')
        
        # Create a new task
        task_id = str(uuid.uuid4())
        creation_time = time.time()
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Log the task being added
            logging.info(f"Adding task: ID={task_id}, Title={params['title']}, Client={client_id}")
            
            cursor.execute('''
            INSERT INTO tasks (
                id, client_id, title, description, due_date, priority,
                completed, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id,
                client_id,
                params['title'],
                params.get('description', ''),
                params.get('due_date'),
                params.get('priority', 'medium'),
                0,  # completed = False
                creation_time,
                creation_time
            ))
            
            # Make sure to commit the transaction
            conn.commit()
            
            # Verify that the task was added by querying it
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            added_task = cursor.fetchone()
            if added_task:
                logging.info(f"Task successfully stored in database: {added_task}")
            else:
                logging.warning(f"Task not found in database after adding: {task_id}")
            
            return {
                "status": "success",
                "message": f"Task '{params['title']}' added successfully",
                "task_id": task_id
            }
        except sqlite3.Error as e:
            logging.error(f"Error adding task: {str(e)}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}"
            }
    
    def get_tasks(self, params, **kwargs):
        """Get a user's todo list tasks
        
        Args:
            params: Dictionary with filter parameters (include_completed)
            kwargs: Additional parameters including client_id
            
        Returns:
            Dictionary with status and tasks list
        """
        client_id = kwargs.get('client_id', 'anonymous')
        include_completed = params.get('include_completed', False)
        
        try:
            conn = self.db_manager.get_connection()
            # The row_factory is already set in the connection
            cursor = conn.cursor()
            
            # Log the request parameters
            logging.info(f"Getting tasks for client_id={client_id}, include_completed={include_completed}")
            
            # Build query based on parameters
            query = "SELECT * FROM tasks WHERE client_id = ?"
            query_params = [client_id]
            
            if not include_completed:
                query += " AND completed = 0"
            
            # Sort by due date and priority
            query += " ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC, "
            query += "CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END"
            
            logging.info(f"Executing query: {query} with params: {query_params}")
            cursor.execute(query, query_params)
            tasks = cursor.fetchall()
            logging.info(f"Retrieved {len(tasks)} tasks from database")
            
            # Ensure proper data format for tasks
            formatted_tasks = []
            for task in tasks:
                # Convert SQLite boolean (0/1) to Python boolean
                if task is not None:
                    if 'completed' in task:
                        task['completed'] = bool(task['completed'])
                    formatted_tasks.append(task)
                    logging.debug(f"Formatted task: {task}")
            
            return {
                "status": "success",
                "tasks": formatted_tasks,
                "message": f"Found {len(formatted_tasks)} tasks" if formatted_tasks else "No tasks found"
            }
        except sqlite3.Error as e:
            logging.error(f"Error getting tasks: {str(e)}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}"
            }
    
    def update_task(self, params, **kwargs):
        """Update a task in a user's todo list
        
        Args:
            params: Dictionary with task details (task_id required, plus fields to update)
            kwargs: Additional parameters including client_id
            
        Returns:
            Dictionary with status, message and updated task
        """
        if 'task_id' not in params:
            return {"error": "Missing required parameter 'task_id'"}
        
        client_id = kwargs.get('client_id', 'anonymous')
        task_id = params['task_id']
        
        try:
            conn = self.db_manager.get_connection()
            # The row_factory is already set in the connection
            cursor = conn.cursor()
            
            # Check if task exists and belongs to the user
            cursor.execute(
                "SELECT * FROM tasks WHERE id = ? AND client_id = ?",
                (task_id, client_id)
            )
            task = cursor.fetchone()
            
            if not task:
                return {
                    "status": "error",
                    "message": f"Task with ID '{task_id}' not found or access denied"
                }
            
            # Build update query based on provided parameters
            update_fields = []
            update_values = []
            
            for field in ['title', 'description', 'due_date', 'priority']:
                if field in params:
                    update_fields.append(f"{field} = ?")
                    update_values.append(params[field])
            
            if 'completed' in params:
                update_fields.append("completed = ?")
                update_values.append(1 if params['completed'] else 0)
            
            if not update_fields:
                return {
                    "status": "error",
                    "message": "No fields to update provided"
                }
            
            # Add updated_at field
            update_fields.append("updated_at = ?")
            update_values.append(time.time())
            
            # Add task_id and client_id for WHERE clause
            update_values.append(task_id)
            update_values.append(client_id)
            
            # Execute update
            cursor.execute(
                f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ? AND client_id = ?",
                tuple(update_values)
            )
            
            conn.commit()
            
            # Get updated task
            cursor.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,)
            )
            updated_task = cursor.fetchone()
            
            # Ensure task data is valid and properly formatted
            if updated_task is not None:
                # Convert SQLite boolean to Python boolean
                if 'completed' in updated_task:
                    updated_task['completed'] = bool(updated_task['completed'])
            
            return {
                "status": "success",
                "message": "Task updated successfully",
                "task": updated_task
            }
        except sqlite3.Error as e:
            logging.error(f"Error updating task: {str(e)}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}"
            }
    
    def delete_task(self, params, **kwargs):
        """Delete a task from a user's todo list
        
        Args:
            params: Dictionary with task_id
            kwargs: Additional parameters including client_id
            
        Returns:
            Dictionary with status and message
        """
        if 'task_id' not in params:
            return {"error": "Missing required parameter 'task_id'"}
        
        client_id = kwargs.get('client_id', 'anonymous')
        task_id = params['task_id']
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get task title before deleting (for confirmation message)
            cursor.execute(
                "SELECT title FROM tasks WHERE id = ? AND client_id = ?",
                (task_id, client_id)
            )
            task = cursor.fetchone()
            
            if not task:
                return {
                    "status": "error",
                    "message": f"Task with ID '{task_id}' not found or access denied"
                }
            
            task_title = task[0]
            
            # Delete the task
            cursor.execute(
                "DELETE FROM tasks WHERE id = ? AND client_id = ?",
                (task_id, client_id)
            )
            
            conn.commit()
            
            return {
                "status": "success",
                "message": f"Task '{task_title}' deleted successfully"
            }
        except sqlite3.Error as e:
            logging.error(f"Error deleting task: {str(e)}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}"
            }
    
    def _dict_factory(self, cursor, row):
        """Convert SQLite row to dictionary"""
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
    
    def close(self):
        """Close the database connection for the current thread"""
        self.db_manager.close()
    
    def close_all(self):
        """Close all database connections (should be called on server shutdown)"""
        self.db_manager.close_all()
        logging.info("All database connections closed")
