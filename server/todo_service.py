import json
import time
import uuid
from datetime import datetime

class TodoService:
    """Todo list service for the distributed system"""
    
    def __init__(self):
        self.todos = {}  # user_id -> list of todos
    
    def add_task(self, params, **kwargs):
        """Add a task to a user's todo list"""
        if 'title' not in params:
            return {"error": "Missing required parameter 'title'"}
        
        client_id = kwargs.get('client_id', 'anonymous')
        
        # Initialize user's todo list if not exists
        if client_id not in self.todos:
            self.todos[client_id] = []
        
        # Create a new task
        task_id = str(uuid.uuid4())
        creation_time = time.time()
        
        task = {
            'id': task_id,
            'title': params['title'],
            'description': params.get('description', ''),
            'due_date': params.get('due_date'),
            'priority': params.get('priority', 'medium'),
            'completed': False,
            'created_at': creation_time,
            'updated_at': creation_time
        }
        
        # Add the task to the user's list
        self.todos[client_id].append(task)
        
        return {
            "status": "success",
            "message": f"Task '{task['title']}' added successfully",
            "task_id": task_id
        }
    
    def get_tasks(self, params, **kwargs):
        """Get a user's todo list tasks"""
        client_id = kwargs.get('client_id', 'anonymous')
        include_completed = params.get('include_completed', False)
        
        # Check if user has any tasks
        if client_id not in self.todos or not self.todos[client_id]:
            return {
                "status": "success",
                "tasks": [],
                "message": "No tasks found"
            }
        
        # Filter tasks based on parameters
        tasks = self.todos[client_id]
        
        if not include_completed:
            tasks = [task for task in tasks if not task['completed']]
        
        # Sort tasks by due date and priority
        def task_sort_key(task):
            due_date = task.get('due_date')
            if due_date:
                try:
                    due_date = datetime.strptime(due_date, "%Y-%m-%d").timestamp()
                except ValueError:
                    due_date = float('inf')
            else:
                due_date = float('inf')
                
            priority_value = {
                'high': 0,
                'medium': 1,
                'low': 2
            }.get(task.get('priority', 'medium'), 1)
            
            return (due_date, priority_value)
        
        sorted_tasks = sorted(tasks, key=task_sort_key)
        
        return {
            "status": "success",
            "tasks": sorted_tasks
        }
    
    def update_task(self, params, **kwargs):
        """Update a task in a user's todo list"""
        if 'task_id' not in params:
            return {"error": "Missing required parameter 'task_id'"}
        
        client_id = kwargs.get('client_id', 'anonymous')
        task_id = params['task_id']
        
        # Check if user has any tasks
        if client_id not in self.todos or not self.todos[client_id]:
            return {
                "status": "error",
                "message": "No tasks found for this user"
            }
        
        # Find the task
        for i, task in enumerate(self.todos[client_id]):
            if task['id'] == task_id:
                # Update task fields
                for key in ['title', 'description', 'due_date', 'priority', 'completed']:
                    if key in params:
                        task[key] = params[key]
                
                task['updated_at'] = time.time()
                self.todos[client_id][i] = task
                
                return {
                    "status": "success",
                    "message": f"Task '{task['title']}' updated successfully",
                    "task": task
                }
        
        return {
            "status": "error",
            "message": f"Task with ID '{task_id}' not found"
        }
    
    def delete_task(self, params, **kwargs):
        """Delete a task from a user's todo list"""
        if 'task_id' not in params:
            return {"error": "Missing required parameter 'task_id'"}
        
        client_id = kwargs.get('client_id', 'anonymous')
        task_id = params['task_id']
        
        # Check if user has any tasks
        if client_id not in self.todos or not self.todos[client_id]:
            return {
                "status": "error",
                "message": "No tasks found for this user"
            }
        
        # Find and remove the task
        for i, task in enumerate(self.todos[client_id]):
            if task['id'] == task_id:
                task_title = task['title']
                del self.todos[client_id][i]
                
                return {
                    "status": "success",
                    "message": f"Task '{task_title}' deleted successfully"
                }
        
        return {
            "status": "error",
            "message": f"Task with ID '{task_id}' not found"
        }