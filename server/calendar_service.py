import json
import time
import uuid
from datetime import datetime, timedelta

class CalendarService:
    """Calendar service for the distributed system"""
    
    def __init__(self):
        self.events = {}  # user_id -> list of events
    
    def add_event(self, params, **kwargs):
        """Add an event to a user's calendar"""
        required_params = ['title', 'start_time']
        for param in required_params:
            if param not in params:
                return {"error": f"Missing required parameter '{param}'"}
        
        client_id = kwargs.get('client_id', 'anonymous')
        
        # Initialize user's calendar if not exists
        if client_id not in self.events:
            self.events[client_id] = []
        
        # Create a new event
        event_id = str(uuid.uuid4())
        creation_time = time.time()
        
        # Parse dates/times
        try:
            start_time = self._parse_datetime(params['start_time'])
            end_time = self._parse_datetime(params.get('end_time', '')) if 'end_time' in params else start_time + timedelta(hours=1)
        except ValueError as e:
            return {"error": f"Invalid date/time format: {str(e)}"}
        
        # Create event object
        event = {
            'id': event_id,
            'title': params['title'],
            'description': params.get('description', ''),
            'location': params.get('location', ''),
            'start_time': start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            'end_time': end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            'all_day': params.get('all_day', False),
            'created_at': creation_time,
            'updated_at': creation_time
        }
        
        # Add the event to the user's calendar
        self.events[client_id].append(event)
        
        return {
            "status": "success",
            "message": f"Event '{event['title']}' added successfully",
            "event_id": event_id
        }
    
    def get_today_events(self, params, **kwargs):
        """Get a user's calendar events for today using system time"""
        # Get today's date from the system
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        
        # Format dates for the local method's params
        today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Use the existing get_events method with today's dates
        return self.get_events({
            "start_date": today_start.strftime("%Y-%m-%dT%H:%M:%S"),
            "end_date": today_end.strftime("%Y-%m-%dT%H:%M:%S")
        }, **kwargs)
    
    def get_events(self, params, **kwargs):
        """Get a user's calendar events"""
        client_id = kwargs.get('client_id', 'anonymous')
        
        # Parse date range if provided
        start_date = None
        end_date = None
        
        if 'start_date' in params:
            try:
                start_date = self._parse_datetime(params['start_date'])
            except ValueError:
                return {"error": "Invalid start_date format"}
        
        if 'end_date' in params:
            try:
                end_date = self._parse_datetime(params['end_date'])
            except ValueError:
                return {"error": "Invalid end_date format"}
        
        # If no start date is provided, use today
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # If no end date is provided, use start date + 7 days
        if end_date is None:
            end_date = start_date + timedelta(days=7)
        
        # Check if user has any events
        if client_id not in self.events or not self.events[client_id]:
            return {
                "status": "success",
                "events": [],
                "message": "No events found"
            }
        
        # Filter events based on date range
        filtered_events = []
        for event in self.events[client_id]:
            event_start = datetime.strptime(event['start_time'], "%Y-%m-%dT%H:%M:%S")
            event_end = datetime.strptime(event['end_time'], "%Y-%m-%dT%H:%M:%S")
            
            # Check if event falls within the date range
            if (event_start <= end_date and event_end >= start_date):
                filtered_events.append(event)
        
        # Sort events by start time
        sorted_events = sorted(filtered_events, key=lambda e: e['start_time'])
        
        return {
            "status": "success",
            "events": sorted_events,
            "period": {
                "start": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
                "end": end_date.strftime("%Y-%m-%dT%H:%M:%S")
            }
        }
    
    def update_event(self, params, **kwargs):
        """Update an event in a user's calendar"""
        if 'event_id' not in params:
            return {"error": "Missing required parameter 'event_id'"}
        
        client_id = kwargs.get('client_id', 'anonymous')
        event_id = params['event_id']
        
        # Check if user has any events
        if client_id not in self.events or not self.events[client_id]:
            return {
                "status": "error",
                "message": "No events found for this user"
            }
        
        # Find the event
        for i, event in enumerate(self.events[client_id]):
            if event['id'] == event_id:
                # Update event fields
                for key in ['title', 'description', 'location', 'all_day']:
                    if key in params:
                        event[key] = params[key]
                
                # Handle date/time updates
                for time_key in ['start_time', 'end_time']:
                    if time_key in params:
                        try:
                            parsed_time = self._parse_datetime(params[time_key])
                            event[time_key] = parsed_time.strftime("%Y-%m-%dT%H:%M:%S")
                        except ValueError as e:
                            return {"error": f"Invalid {time_key} format: {str(e)}"}
                
                event['updated_at'] = time.time()
                self.events[client_id][i] = event
                
                return {
                    "status": "success",
                    "message": f"Event '{event['title']}' updated successfully",
                    "event": event
                }
        
        return {
            "status": "error",
            "message": f"Event with ID '{event_id}' not found"
        }
    
    def delete_event(self, params, **kwargs):
        """Delete an event from a user's calendar"""
        if 'event_id' not in params:
            return {"error": "Missing required parameter 'event_id'"}
        
        client_id = kwargs.get('client_id', 'anonymous')
        event_id = params['event_id']
        
        # Check if user has any events
        if client_id not in self.events or not self.events[client_id]:
            return {
                "status": "error",
                "message": "No events found for this user"
            }
        
        # Find and remove the event
        for i, event in enumerate(self.events[client_id]):
            if event['id'] == event_id:
                event_title = event['title']
                del self.events[client_id][i]
                
                return {
                    "status": "success",
                    "message": f"Event '{event_title}' deleted successfully"
                }
        
        return {
            "status": "error",
            "message": f"Event with ID '{event_id}' not found"
        }
    
    def _parse_datetime(self, datetime_str):
        """Parse a datetime string in various formats"""
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Could not parse datetime: {datetime_str}")