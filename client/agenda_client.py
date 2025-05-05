import sys
import time
import random
import logging
import time
import sys
from datetime import datetime
import os
import json

from client.multi_client import MultiServerClient

class AgendaClient:
    """Client for comprehensive daily agendas using multiple services"""
    
    def __init__(self, weather_server="localhost:50052", todo_server="localhost:50053", calendar_server="localhost:50054", client_id="interactive_user"):
        """Initialize the agenda client with connections to all services
        
        Args:
            weather_server: Address of the weather server
            todo_server: Address of the todo server
            calendar_server: Address of the calendar server
            client_id: The client ID to use for all operations
        """
        self.client_id = client_id
        logging.info(f"Initializing agenda client with client_id: {self.client_id}")
        
        # Create a client that can talk to all three servers
        self.client = MultiServerClient({
            "weather": weather_server,
            "todo": todo_server,
            "calendar": calendar_server
        }, default_client_id=client_id)
        
        # Display service information
        self.show_service_info()
    
    def generate_daily_agenda(self):
        """Generate a comprehensive daily agenda"""
        try:
            # Update the client object with our client ID - this will explicitly override
            # any other client IDs that might have been set elsewhere
            self.client.client_id = self.client_id
            logging.info(f"Generating agenda with client_id: {self.client_id}")
            
            # Generate agenda and update display
            try:
                agenda = self.client.generate_agenda()
                # Debug the agenda data
                logging.info(f"Raw agenda data: {json.dumps(agenda)}")
                formatted_agenda = self._format_agenda(agenda)
                print("\nUpdating your agenda...\n")
                print(formatted_agenda)
                return formatted_agenda
            except Exception as e:
                logging.error(f"Error generating agenda: {str(e)}")
                print(f"Error generating agenda: {str(e)}")
        except Exception as e:
            logging.error(f"Error generating agenda: {str(e)}")
            print(f"Error generating agenda: {str(e)}")
    
    def show_service_info(self):
        """Display information about the connected services"""
        print("Connecting to services and checking implementations...")
        
        # Check each server for service info
        service_info = {}
        for server_type in ["weather", "todo", "calendar"]:
            if server_type not in self.client.servers or not self.client.servers[server_type].connected:
                print(f"❌ {server_type.capitalize()} Service: Not connected")
                continue
                
            try:
                # Try to get service info by calling the get_service_info method
                result = self.client.invoke_method(server_type, "get_service_info", {})
                if result and "error" not in result:
                    service_info[server_type] = result
                    
                    implementation = result.get("implementation", "Unknown")
                    status_icon = "✅" if "Mock" not in implementation else "ℹ️"
                    
                    if server_type == "calendar" and implementation == "Google Calendar":
                        auth_status = result.get("authentication_status", "Unknown")
                        if auth_status != "Authenticated":
                            status_icon = "⚠️"
                            implementation += f" ({auth_status})"
                    
                    print(f"{status_icon} {server_type.capitalize()} Service: {implementation}")
                else:
                    print(f"ℹ️ {server_type.capitalize()} Service: Connected but no implementation info")
            except Exception as e:
                logging.error(f"Error getting service info for {server_type}: {str(e)}")
                print(f"ℹ️ {server_type.capitalize()} Service: Connected")
        
        print()
        return service_info
        
    def _format_agenda(self, agenda):
        """Format the agenda data into a readable format"""
        today = datetime.now()
        date_str = today.strftime("%A, %B %d, %Y")
        
        formatted = f"📅 Daily Agenda for {date_str}\n"
        formatted += "=" * 50 + "\n\n"
        
        # Add weather section
        if agenda.get("weather") and agenda["weather"].get("status") == "success":
            weather = agenda["weather"]
            location = weather.get("location", "Unknown location")
            w_data = weather.get("weather", {})
            condition = w_data.get("condition", "Unknown")
            temp = w_data.get("temperature", "?")
            
            formatted += f"🌤️  Weather in {location}: {condition}, {temp}°C\n\n"
        
        # Add calendar events
        formatted += "📆 Today's Schedule:\n"
        if agenda.get("events") and len(agenda["events"]) > 0:
            events = sorted(agenda["events"], key=lambda e: e.get("start_time", ""))
            for event in events:
                title = event.get("title", "Untitled Event")
                start = event.get("start_time", "")
                end = event.get("end_time", "")
                location = event.get("location", "")
                
                # Format time
                time_str = ""
                if start:
                    try:
                        start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
                        time_str = start_dt.strftime("%I:%M %p")
                        
                        if end:
                            end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")
                            time_str += f" - {end_dt.strftime('%I:%M %p')}"
                    except ValueError:
                        time_str = start
                
                loc_str = f" at {location}" if location else ""
                formatted += f"  • {time_str}: {title}{loc_str}\n"
        else:
            formatted += "  No scheduled events for today.\n"
        
        # Add tasks
        formatted += "\n✅ To-Do List:\n"
        if agenda.get("tasks") and isinstance(agenda["tasks"], list) and len(agenda["tasks"]) > 0:
            valid_tasks = []
            
            # Filter out None tasks or tasks with missing required fields
            for task in agenda["tasks"]:
                if task is not None and isinstance(task, dict) and "title" in task:
                    valid_tasks.append(task)
                    
            if valid_tasks:
                # Sort tasks by priority and due date with safe default values
                try:
                    # Debug the task data
                    logging.info(f"Task data before sorting: {json.dumps(valid_tasks)}")
                    
                    # Define a custom sorting function to handle None values
                    def task_sort_key(task):
                        # Handle priority
                        priority_map = {"high": 0, "medium": 1, "low": 2}
                        priority = task.get("priority", "medium")
                        priority_val = priority_map.get(priority, 1) if priority else 1
                        
                        # Handle due date - convert None or empty string to far future date
                        due_date = task.get("due_date", None)
                        if not due_date:  # Handle None or empty string
                            return (priority_val, "9999-99-99")
                        return (priority_val, due_date)
                    
                    # Sort tasks using the custom key function
                    tasks = sorted(valid_tasks, key=task_sort_key)
                    logging.info(f"Sorted {len(tasks)} tasks successfully")
                except Exception as e:
                    logging.error(f"Error sorting tasks: {str(e)}")
                    tasks = valid_tasks  # Use unsorted tasks if sorting fails
                
                for task in tasks:
                    title = task.get("title", "Untitled Task")
                    priority = task.get("priority", "medium")
                    due_date = task.get("due_date", "")
                    
                    # Set the emoji based on priority
                    emoji = "🔴" if priority == "high" else "🟠" if priority == "medium" else "🟢"
                    
                    # Add the due date if available
                    due_str = f" (Due: {due_date})" if due_date else ""
                    formatted += f"  {emoji} {title}{due_str}\n"
            else:
                formatted += "  No valid tasks found.\n"
        else:
            formatted += "  No pending tasks for today.\n"
        
        formatted += "\n" + "=" * 50 + "\n"
        formatted += "Have a productive day! 🚀"
        
        return formatted
    
    def add_calendar_event(self, title, start_time, end_time=None, location=None):
        """Add an event to the calendar"""
        params = {
            "title": title,
            "start_time": start_time
        }
        
        if end_time:
            params["end_time"] = end_time
        
        if location:
            params["location"] = location
        
        return self.client.invoke_method("calendar", "add_event", params)
    
    def add_task(self, title, description=None, due_date=None, priority="medium"):
        """Add a task to the todo list"""
        params = {
            "title": title
        }
        
        if description:
            params["description"] = description
        
        if due_date:
            params["due_date"] = due_date
        
        if priority:
            params["priority"] = priority
        
        return self.client.invoke_method("todo", "add_task", params, client_id=self.client_id)
    
    def get_weather(self, location="Boston"):
        """Get weather for a location"""
        return self.client.invoke_method("weather", "get_current_weather", {"location": location})
    
    def close(self):
        """Close all connections"""
        self.client.close()

def run_interactive_agenda_client():
    """Run an interactive agenda client"""
    # Create agenda client with a consistent client ID
    try:
        client = AgendaClient(client_id="interactive_user")
    except Exception as e:
        print(f"Failed to initialize client: {str(e)}")
        return
    
    print("\n" + "=" * 60)
    print("🤖 Welcome to the Distributed Agenda System")
    print("=" * 60)
    print("\nConnecting to services...")
    
    # Add some demo data
    try:
        # Add calendar events
        client.add_calendar_event(
            "Team Meeting",
            datetime.now().strftime("%Y-%m-%d") + "T10:00:00",
            datetime.now().strftime("%Y-%m-%d") + "T11:00:00",
            "Conference Room 3"
        )
        
        client.add_calendar_event(
            "Lunch with Alex",
            datetime.now().strftime("%Y-%m-%d") + "T12:30:00",
            datetime.now().strftime("%Y-%m-%d") + "T13:30:00",
            "Café Paradiso"
        )
        
        client.add_calendar_event(
            "Project Review",
            datetime.now().strftime("%Y-%m-%d") + "T15:00:00",
            datetime.now().strftime("%Y-%m-%d") + "T16:00:00"
        )
        
        # Add tasks
        client.add_task(
            "Prepare presentation slides",
            "Create slides for tomorrow's client meeting",
            datetime.now().strftime("%Y-%m-%d"),
            "high"
        )
        
        client.add_task(
            "Review pull requests",
            "Check and merge team PRs",
            datetime.now().strftime("%Y-%m-%d"),
            "medium"
        )
        
        client.add_task(
            "Update documentation",
            "Update API docs with new endpoints",
            (datetime.now().strftime("%Y-%m-%d")),
            "low"
        )
        
        print("Demo data loaded successfully.")
    except Exception as e:
        print(f"Error loading demo data: {str(e)}")
    
    # Display the agenda
    print("\nGenerating your daily agenda...\n")
    time.sleep(1)  # Simulate processing time
    
    agenda = client.generate_daily_agenda()
    print(agenda)
    
    print("\n" + "=" * 60)
    print("Available Commands:")
    print("  agenda - Display your daily agenda")
    print("  add event - Add a calendar event")
    print("  add task - Add a todo task")
    print("  weather [location] - Get weather for a location")
    print("  exit - Exit the application")
    print("=" * 60)
    
    # Interactive loop
    while True:
        try:
            command = input("\n> ").strip().lower()
            
            if command == "exit" or command == "quit":
                break
            
            elif command == "agenda":
                print("\nUpdating your agenda...\n")
                time.sleep(0.5)
                agenda = client.generate_daily_agenda()
                print(agenda)
            
            elif command.startswith("add event"):
                title = input("Event title: ")
                start_date = input("Start date and time (YYYY-MM-DD HH:MM): ")
                end_date = input("End date and time (YYYY-MM-DD HH:MM) [optional]: ")
                location = input("Location [optional]: ")
                
                if not end_date:
                    end_date = None
                    
                if not location:
                    location = None
                
                result = client.add_calendar_event(title, start_date, end_date, location)
                print(f"Event added: {result.get('message', 'Success')}")
            
            elif command.startswith("add task"):
                title = input("Task title: ")
                description = input("Description [optional]: ")
                due_date = input("Due date (YYYY-MM-DD) [optional]: ")
                priority = input("Priority (high/medium/low) [default: medium]: ")
                
                if not description:
                    description = None
                
                if not due_date:
                    due_date = None
                
                if not priority:
                    priority = "medium"
                
                result = client.add_task(title, description, due_date, priority)
                print(f"Task added: {result.get('message', 'Success')}")
            
            elif command.startswith("weather"):
                parts = command.split(maxsplit=1)
                location = parts[1] if len(parts) > 1 else "Boston"
                
                print(f"Getting weather for {location}...")
                result = client.get_weather(location)
                
                if result.get("status") == "success":
                    w_data = result.get("weather", {})
                    condition = w_data.get("condition", "Unknown")
                    temp = w_data.get("temperature", "?")
                    humidity = w_data.get("humidity", "?")
                    wind = w_data.get("wind_speed", "?")
                    
                    print(f"\n🌤️  Weather in {location.title()}:")
                    print(f"  Condition: {condition}")
                    print(f"  Temperature: {temp}°C")
                    print(f"  Humidity: {humidity}%")
                    print(f"  Wind Speed: {wind} km/h")
                else:
                    print(f"Error: {result.get('message', 'Unknown error')}")
            
            else:
                print("Unknown command. Type 'agenda', 'add event', 'add task', 'weather [location]', or 'exit'.")
        except Exception as e:
            print(f"Error processing command: {str(e)}")


def main():
    """Main function to run the Agenda Client"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🤖 Welcome to the Distributed Agenda System")
    print("============================================================")
    print()
    try:
        run_interactive_agenda_client()
    except Exception as e:
        print(f"Error: {str(e)}")
    
    print("\nThank you for using the Distributed Agenda System. Goodbye!")


if __name__ == "__main__":
    main()