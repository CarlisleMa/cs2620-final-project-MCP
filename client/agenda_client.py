import sys
import time
import random
import logging
import json
from datetime import datetime
from client.multi_client import MultiServerClient

class AgendaClient:
    """Client application that generates daily agendas using multiple servers"""
    
    def __init__(self, client_id="client1", api_key="sk_client1_12345abcde"):
        self.client = MultiServerClient(client_id, api_key)
        self.setup_servers()
    
    def setup_servers(self):
        """Connect to all required servers"""
        servers = [
            ("weather", "localhost:50052"),
            ("todo", "localhost:50053"),
            ("calendar", "localhost:50054")
        ]
        
        for server_type, address in servers:
            if not self.client.add_server(server_type, address):
                print(f"⚠️ Warning: Could not connect to {server_type} server")
    
    def generate_daily_agenda(self):
        """Generate a comprehensive daily agenda"""
        try:
            # Get raw agenda data from servers
            raw_agenda = self.client.generate_agenda()
            
            # Format it nicely
            return self._format_agenda(raw_agenda)
        except Exception as e:
            logging.error(f"Error generating agenda: {str(e)}")
            return f"Error generating agenda: {str(e)}"
    
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
        if agenda.get("tasks") and len(agenda["tasks"]) > 0:
            # Sort tasks by priority and due date
            tasks = sorted(
                agenda["tasks"],
                key=lambda t: (
                    {"high": 0, "medium": 1, "low": 2}.get(t.get("priority", "medium"), 1),
                    t.get("due_date", "9999-99-99")
                )
            )
            
            for task in tasks:
                title = task.get("title", "Untitled Task")
                priority = task.get("priority", "medium")
                due_date = task.get("due_date", "")
                
                priority_symbol = {
                    "high": "🔴",
                    "medium": "🟠",
                    "low": "🟢"
                }.get(priority, "🟠")
                
                due_str = f" (Due: {due_date})" if due_date else ""
                formatted += f"  {priority_symbol} {title}{due_str}\n"
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
        
        return self.client.invoke_method("todo", "add_task", params)
    
    def get_weather(self, location="Boston"):
        """Get weather for a location"""
        return self.client.invoke_method("weather", "get_current_weather", {"location": location})
    
    def close(self):
        """Close all connections"""
        self.client.close()

def run_interactive_agenda_client():
    """Run an interactive agenda client"""
    client = AgendaClient()
    
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
            print(f"Error: {str(e)}")
    
    print("\nThank you for using the Distributed Agenda System. Goodbye!")
    client.close()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    run_interactive_agenda_client()