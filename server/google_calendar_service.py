import os
import json
import time
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import pytz

# Google API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Constants for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'

class GoogleCalendarService:
    """Calendar service that integrates with Google Calendar"""
    
    def __init__(self):
        """Initialize the Google Calendar service"""
        # Load environment variables
        load_dotenv()
        
        # Create credentials directory if it doesn't exist
        creds_dir = Path(__file__).parent.parent / 'credentials'
        os.makedirs(creds_dir, exist_ok=True)
        
        self.token_path = creds_dir / TOKEN_FILE
        self.credentials_path = creds_dir / CREDENTIALS_FILE
        
        # Credentials for Google Calendar API
        self.creds = None
        self.service = None
        
        # Try to initialize the service
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize the Google Calendar API service"""
        # Check if token.json exists
        if os.path.exists(self.token_path):
            try:
                token_content = self.token_path.read_text()
                logging.info(f"Found token.json at {self.token_path}")
                token_data = json.loads(token_content)
                logging.info(f"Token keys: {list(token_data.keys())}")
                
                self.creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                logging.info("Successfully loaded credentials from token.json")
            except Exception as e:
                logging.error(f"Error loading credentials: {str(e)}")
        
        # If credentials don't exist or are invalid, run the OAuth flow
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logging.error(f"Error refreshing credentials: {str(e)}")
                    self.creds = None
            
            # Check if credentials.json exists
            if not os.path.exists(self.credentials_path):
                logging.warning(
                    "Google Calendar credentials file not found. "
                    "Please place your credentials.json file in the credentials directory."
                )
                return
            
            # Run the OAuth flow
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
                
                # Save the credentials for future use
                self.token_path.write_text(
                    json.dumps({
                        'token': self.creds.token,
                        'refresh_token': self.creds.refresh_token,
                        'token_uri': self.creds.token_uri,
                        'client_id': self.creds.client_id,
                        'client_secret': self.creds.client_secret,
                        'scopes': self.creds.scopes
                    })
                )
                logging.info("Google Calendar credentials saved successfully")
            except Exception as e:
                logging.error(f"Error during OAuth flow: {str(e)}")
                return
        
        # Build the Google Calendar service
        try:
            self.service = build('calendar', 'v3', credentials=self.creds)
            logging.info("Google Calendar service initialized successfully")
        except Exception as e:
            logging.error(f"Error building Google Calendar service: {str(e)}")
    
    def _ensure_service(self):
        """Ensure the Google Calendar service is initialized"""
        if not self.service:
            logging.warning("Google Calendar service not initialized. Attempting to initialize...")
            self._initialize_service()
            
            if not self.service:
                raise Exception("Failed to initialize Google Calendar service")
    
    def add_event(self, params, **kwargs):
        """Add an event to a user's Google Calendar"""
        required_params = ['title', 'start_time']
        for param in required_params:
            if param not in params:
                return {"error": f"Missing required parameter '{param}'"}
        
        client_id = kwargs.get('client_id', 'primary')
        calendar_id = 'primary'  # Use the user's primary calendar
        
        # Ensure service is initialized
        try:
            self._ensure_service()
        except Exception as e:
            return {"error": f"Google Calendar service error: {str(e)}"}
        
        # Parse dates/times
        try:
            start_time = self._parse_datetime(params['start_time'])
            end_time = self._parse_datetime(params.get('end_time', '')) if 'end_time' in params else start_time + timedelta(hours=1)
        except ValueError as e:
            return {"error": f"Invalid date/time format: {str(e)}"}
        
        # Create Google Calendar event
        event = {
            'summary': params['title'],
            'description': params.get('description', ''),
            'location': params.get('location', ''),
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/New_York',  # TODO: Make this configurable
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/New_York',  # TODO: Make this configurable
            },
        }
        
        # If all-day event
        if params.get('all_day', False):
            event['start'] = {'date': start_time.date().isoformat()}
            event['end'] = {'date': end_time.date().isoformat()}
        
        try:
            result = self.service.events().insert(calendarId=calendar_id, body=event).execute()
            
            # Format the response
            return {
                "status": "success",
                "message": f"Event '{params['title']}' added successfully to Google Calendar",
                "event_id": result['id']
            }
        except HttpError as e:
            error_message = json.loads(e.content).get('error', {}).get('message', str(e))
            logging.error(f"Google Calendar API error: {error_message}")
            return {"error": f"Google Calendar API error: {error_message}"}
        except Exception as e:
            logging.error(f"Error adding event to Google Calendar: {str(e)}")
            return {"error": f"Error adding event to Google Calendar: {str(e)}"}
    
    def get_today_events(self, params, **kwargs):
        """Get today's events from a user's Google Calendar using system time"""
        client_id = kwargs.get('client_id', 'primary')
        calendar_id = 'primary'  # Use the user's primary calendar
        
        # Ensure service is initialized
        try:
            self._ensure_service()
        except Exception as e:
            return {"error": f"Google Calendar service error: {str(e)}"}
            
        # Get today's date from the system
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        
        # Format dates for the API (ISO format)
        today_start = today.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_end = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        logging.info(f"Getting today's events from {today_start} to {today_end}")
        
        # Use the get_events method with today's date
        return self.get_events({
            "start_date": today_start,
            "end_date": today_end
        }, **kwargs)
    
    def get_events(self, params, **kwargs):
        """Get events from a user's Google Calendar"""
        client_id = kwargs.get('client_id', 'primary')
        calendar_id = 'primary'  # Use the user's primary calendar
        
        # Ensure service is initialized
        try:
            self._ensure_service()
        except Exception as e:
            return {"error": f"Google Calendar service error: {str(e)}"}
        
        # Parse date range if provided
        time_min = None
        time_max = None
        
        if 'start_date' in params:
            try:
                time_min = self._parse_datetime(params['start_date'])
                logging.info(f"Parsed start_date: {time_min} from {params['start_date']}")
            except ValueError as e:
                logging.error(f"Invalid start_date format: {params['start_date']}, error: {str(e)}")
                return {"error": f"Invalid start_date format: {str(e)}"}
        
        if 'end_date' in params:
            try:
                time_max = self._parse_datetime(params['end_date'])
                logging.info(f"Parsed end_date: {time_max} from {params['end_date']}")
            except ValueError as e:
                logging.error(f"Invalid end_date format: {params['end_date']}, error: {str(e)}")
                return {"error": f"Invalid end_date format: {str(e)}"}
        
        # If no start date is provided, use today
        if time_min is None:
            time_min = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            logging.info(f"No start_date provided, using today: {time_min}")
        
        # If no end date is provided, use start date + 7 days
        if time_max is None:
            time_max = time_min + timedelta(days=7)
            logging.info(f"No end_date provided, using {time_max}")
        
        try:
            # Verify that the service is initialized
            if not self.service:
                logging.error("Google Calendar service not initialized before making API call")
                return {"error": "Google Calendar service not initialized"}
                
            time_min_str = time_min.isoformat() + 'Z'  # 'Z' indicates UTC time
            time_max_str = time_max.isoformat() + 'Z'
            logging.info(f"Fetching events from Google Calendar between {time_min_str} and {time_max_str}")
            
            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min_str,
                timeMax=time_max_str,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            logging.info(f"Successfully retrieved events from Google Calendar API")
            
            # Get events from the response
            google_events = events_result.get('items', [])
            logging.info(f"Retrieved {len(google_events)} events from Google Calendar")
            
            if not google_events:
                logging.info("No events found in Google Calendar for the specified time range")
                return {
                    "status": "success",
                    "events": [],
                    "message": "No events found"
                }
            
            # Convert Google events to our format
            formatted_events = []
            for event in google_events:
                # Handle all-day events
                if 'date' in event.get('start', {}):
                    start_time = datetime.fromisoformat(event['start']['date']).strftime("%Y-%m-%dT%H:%M:%S")
                    end_time = datetime.fromisoformat(event['end']['date']).strftime("%Y-%m-%dT%H:%M:%S")
                    all_day = True
                else:
                    # Regular events with time
                    start_time = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '')).strftime("%Y-%m-%dT%H:%M:%S")
                    end_time = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '')).strftime("%Y-%m-%dT%H:%M:%S")
                    all_day = False
                
                formatted_event = {
                    'id': event['id'],
                    'title': event.get('summary', 'Untitled Event'),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'start_time': start_time,
                    'end_time': end_time,
                    'all_day': all_day,
                    'created_at': time.time(),  # We don't have exact creation time
                    'updated_at': time.time()
                }
                
                formatted_events.append(formatted_event)
            
            return {
                "status": "success",
                "events": formatted_events,
                "message": f"Found {len(formatted_events)} events"
            }
            
        except HttpError as e:
            error_message = json.loads(e.content).get('error', {}).get('message', str(e))
            logging.error(f"Google Calendar API error: {error_message}")
            return {"error": f"Google Calendar API error: {error_message}"}
        except Exception as e:
            logging.error(f"Error retrieving events from Google Calendar: {str(e)}")
            return {"error": f"Error retrieving events from Google Calendar: {str(e)}"}
    
    def update_event(self, params, **kwargs):
        """Update an event in the user's Google Calendar"""
        if 'event_id' not in params:
            return {"error": "Missing required parameter 'event_id'"}
        
        client_id = kwargs.get('client_id', 'primary')
        calendar_id = 'primary'  # Use the user's primary calendar
        event_id = params['event_id']
        
        # Ensure service is initialized
        try:
            self._ensure_service()
        except Exception as e:
            return {"error": f"Google Calendar service error: {str(e)}"}
        
        try:
            # First, get the existing event
            event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            
            # Update the event fields
            if 'title' in params:
                event['summary'] = params['title']
            
            if 'description' in params:
                event['description'] = params['description']
            
            if 'location' in params:
                event['location'] = params['location']
            
            # Handle date/time updates
            if 'start_time' in params or 'end_time' in params:
                try:
                    # Get current start and end times
                    if 'date' in event['start']:
                        # All-day event
                        current_start = datetime.fromisoformat(event['start']['date'])
                        current_end = datetime.fromisoformat(event['end']['date'])
                    else:
                        # Regular event
                        current_start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', ''))
                        current_end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', ''))
                    
                    # Update start time if provided
                    if 'start_time' in params:
                        new_start = self._parse_datetime(params['start_time'])
                    else:
                        new_start = current_start
                    
                    # Update end time if provided
                    if 'end_time' in params:
                        new_end = self._parse_datetime(params['end_time'])
                    else:
                        # Maintain the same duration
                        duration = current_end - current_start
                        new_end = new_start + duration
                    
                    # Update the event
                    if params.get('all_day', False) or ('date' in event['start'] and 'all_day' not in params):
                        # All-day event
                        event['start'] = {'date': new_start.date().isoformat()}
                        event['end'] = {'date': new_end.date().isoformat()}
                    else:
                        # Regular event
                        event['start'] = {
                            'dateTime': new_start.isoformat(),
                            'timeZone': 'America/New_York',  # TODO: Make configurable
                        }
                        event['end'] = {
                            'dateTime': new_end.isoformat(),
                            'timeZone': 'America/New_York',  # TODO: Make configurable
                        }
                    
                except ValueError as e:
                    return {"error": f"Invalid date/time format: {str(e)}"}
            
            # Update the event in Google Calendar
            updated_event = self.service.events().update(
                calendarId=calendar_id, eventId=event_id, body=event).execute()
            
            return {
                "status": "success",
                "message": "Event updated successfully",
                "event_id": updated_event['id']
            }
            
        except HttpError as e:
            error_message = json.loads(e.content).get('error', {}).get('message', str(e))
            logging.error(f"Google Calendar API error: {error_message}")
            return {"error": f"Google Calendar API error: {error_message}"}
        except Exception as e:
            logging.error(f"Error updating event in Google Calendar: {str(e)}")
            return {"error": f"Error updating event in Google Calendar: {str(e)}"}
    
    def delete_event(self, params, **kwargs):
        """Delete an event from the user's Google Calendar"""
        if 'event_id' not in params:
            return {"error": "Missing required parameter 'event_id'"}
        
        client_id = kwargs.get('client_id', 'primary')
        calendar_id = 'primary'  # Use the user's primary calendar
        event_id = params['event_id']
        
        # Ensure service is initialized
        try:
            self._ensure_service()
        except Exception as e:
            return {"error": f"Google Calendar service error: {str(e)}"}
        
        try:
            # Delete the event
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            
            return {
                "status": "success",
                "message": "Event deleted successfully"
            }
        except HttpError as e:
            error_message = json.loads(e.content).get('error', {}).get('message', str(e))
            logging.error(f"Google Calendar API error: {error_message}")
    
    logging.info(f"Successfully retrieved events from Google Calendar API")
    
    # Get events from the response
    google_events = events_result.get('items', [])
    logging.info(f"Retrieved {len(google_events)} events from Google Calendar")
    
    if not google_events:
        logging.info("No events found in Google Calendar for the specified time range")
        return {
            "status": "success",
            "events": [],
            "message": "No events found"
        }
    
    # Convert Google events to our format
    formatted_events = []
    for event in google_events:
        # Handle all-day events
        if 'date' in event.get('start', {}):
            start_time = datetime.fromisoformat(event['start']['date']).strftime("%Y-%m-%dT%H:%M:%S")
            end_time = datetime.fromisoformat(event['end']['date']).strftime("%Y-%m-%dT%H:%M:%S")
            all_day = True
        else:
            # Regular events with time
            start_time = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '')).strftime("%Y-%m-%dT%H:%M:%S")
            end_time = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '')).strftime("%Y-%m-%dT%H:%M:%S")
            all_day = False
        
        formatted_event = {
            'id': event['id'],
            'title': event.get('summary', 'Untitled Event'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'start_time': start_time,
            'end_time': end_time,
            'all_day': all_day,
            'created_at': time.time(),  # We don't have exact creation time
            'updated_at': time.time()
        }
        
        formatted_events.append(formatted_event)
    
    return {
        "status": "success",
        "events": formatted_events,
        "message": f"Found {len(formatted_events)} events"
    }
    
except HttpError as e:
    error_message = json.loads(e.content).get('error', {}).get('message', str(e))
    logging.error(f"Google Calendar API error: {error_message}")
    return {"error": f"Google Calendar API error: {error_message}"}
except Exception as e:
    logging.error(f"Error retrieving events from Google Calendar: {str(e)}")
    return {"error": f"Error retrieving events from Google Calendar: {str(e)}"}

def update_event(self, params, **kwargs):
    """Update an event in the user's Google Calendar"""
    if 'event_id' not in params:
        return {"error": "Missing required parameter 'event_id'"}
    
    client_id = kwargs.get('client_id', 'primary')
    calendar_id = 'primary'  # Use the user's primary calendar
    event_id = params['event_id']
    
    # Ensure service is initialized
    try:
        self._ensure_service()
    except Exception as e:
        return {"error": f"Google Calendar service error: {str(e)}"}
    
    try:
        # First, get the existing event
        event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        # Update the event fields
        if 'title' in params:
            event['summary'] = params['title']
        
        if 'description' in params:
            event['description'] = params['description']
        
        if 'location' in params:
            event['location'] = params['location']
        
        # Handle date/time updates
        if 'start_time' in params or 'end_time' in params:
            try:
                # Get current start and end times
                if 'date' in event['start']:
                    # All-day event
                    current_start = datetime.fromisoformat(event['start']['date'])
                    current_end = datetime.fromisoformat(event['end']['date'])
                else:
                    # Regular event
                    current_start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', ''))
                    current_end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', ''))
                
                # Update start time if provided
                if 'start_time' in params:
                    new_start = self._parse_datetime(params['start_time'])
                else:
                    new_start = current_start
                
                # Update end time if provided
                if 'end_time' in params:
                    new_end = self._parse_datetime(params['end_time'])
                else:
                    # Maintain the same duration
                    duration = current_end - current_start
                    new_end = new_start + duration
                
                # Update the event
                if params.get('all_day', False) or ('date' in event['start'] and 'all_day' not in params):
                    # All-day event
                    event['start'] = {'date': new_start.date().isoformat()}
                    event['end'] = {'date': new_end.date().isoformat()}
                else:
                    # Regular event
                    event['start'] = {
                        'dateTime': new_start.isoformat(),
                        'timeZone': 'America/New_York',  # TODO: Make configurable
                    }
                    event['end'] = {
                        'dateTime': new_end.isoformat(),
                        'timeZone': 'America/New_York',  # TODO: Make configurable
                    }
                
            except ValueError as e:
                return {"error": f"Invalid date/time format: {str(e)}"}
        
        # Update the event in Google Calendar
        updated_event = self.service.events().update(
            calendarId=calendar_id, eventId=event_id, body=event).execute()
        
        return {
            "status": "success",
            "message": "Event updated successfully",
            "event_id": updated_event['id']
        }
        
    except HttpError as e:
        error_message = json.loads(e.content).get('error', {}).get('message', str(e))
        logging.error(f"Google Calendar API error: {error_message}")
        return {"error": f"Google Calendar API error: {error_message}"}
    except Exception as e:
        logging.error(f"Error updating event in Google Calendar: {str(e)}")
        return {"error": f"Error updating event in Google Calendar: {str(e)}"}

def delete_event(self, params, **kwargs):
    """Delete an event from the user's Google Calendar"""
    if 'event_id' not in params:
        return {"error": "Missing required parameter 'event_id'"}
    
    client_id = kwargs.get('client_id', 'primary')
    calendar_id = 'primary'  # Use the user's primary calendar
    event_id = params['event_id']
    
    # Ensure service is initialized
    try:
        self._ensure_service()
    except Exception as e:
        return {"error": f"Google Calendar service error: {str(e)}"}
    
    try:
        # Delete the event
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        
        return {
            "status": "success",
            "message": "Event deleted successfully"
        }
    except HttpError as e:
        error_message = json.loads(e.content).get('error', {}).get('message', str(e))
        logging.error(f"Google Calendar API error: {error_message}")
        return {"error": f"Google Calendar API error: {error_message}"}
    except Exception as e:
        logging.error(f"Error deleting event from Google Calendar: {str(e)}")
        return {"error": f"Error deleting event from Google Calendar: {str(e)}"}

def _parse_datetime(self, datetime_str):
    """Parse a datetime string into a datetime object"""
    # Try standard ISO format
    if not datetime_str:
        raise ValueError("Empty datetime string")
        
    try:
        dt = datetime.fromisoformat(datetime_str)
        logging.debug(f"Parsed datetime {datetime_str} as ISO format: {dt}")
        return dt
    except ValueError:
        logging.debug(f"Failed to parse {datetime_str} as ISO format, trying other formats")
        pass
    
    # Try different formats
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(datetime_str, fmt)
            logging.debug(f"Parsed datetime {datetime_str} with format {fmt}: {dt}")
            return dt
        except ValueError:
            continue
    
    error_msg = f"Could not parse datetime: {datetime_str}"
    logging.error(error_msg)
    raise ValueError(error_msg)
            pass
        
        # Try different formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                logging.debug(f"Parsed datetime {datetime_str} with format {fmt}: {dt}")
                return dt
            except ValueError:
                continue
        
        error_msg = f"Could not parse datetime: {datetime_str}"
        logging.error(error_msg)
        raise ValueError(error_msg)
