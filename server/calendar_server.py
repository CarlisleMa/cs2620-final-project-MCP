import grpc
import time
import logging
import os
from concurrent import futures
import protocol_pb2 as pb2
import protocol_pb2_grpc as pb2_grpc
from server.auth_provider import AuthProvider

# Import both the original and Google Calendar Service
from server.calendar_service import CalendarService
from server.google_calendar_service import GoogleCalendarService

class CalendarServer(pb2_grpc.DistributedServiceServicer):
    def __init__(self):
        self.methods = {}
        self.auth_provider = AuthProvider()
        
        # Check if we should use Google Calendar or the mock service
        # Look for credentials or an environment variable
        use_google = os.environ.get('USE_GOOGLE_CALENDAR', 'false').lower() == 'true'
        creds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'credentials.json')
        
        if use_google and os.path.exists(creds_path):
            try:
                logging.info("Initializing Google Calendar integration...")
                self.calendar_service = GoogleCalendarService()
                logging.info("Google Calendar integration enabled!")
            except Exception as e:
                logging.error(f"Failed to initialize Google Calendar: {str(e)}")
                logging.warning("Falling back to mock calendar service")
                self.calendar_service = CalendarService()
        else:
            if use_google:
                logging.warning("Google Calendar credentials not found at: " + creds_path)
                logging.warning("Falling back to mock calendar service")
            else:
                logging.info("Using mock calendar service (set USE_GOOGLE_CALENDAR=true to use Google Calendar)")
            self.calendar_service = CalendarService()
            
        self.register_methods()
        
    def register_methods(self):
        self.methods["add_event"] = {
            "handler": self.calendar_service.add_event,
            "required_permission": "write"
        }
        self.methods["get_events"] = {
            "handler": self.calendar_service.get_events,
            "required_permission": "read"
        }
        self.methods["get_today_events"] = {
            "handler": self.calendar_service.get_today_events,
            "required_permission": "read"
        }
        self.methods["get_service_info"] = {
            "handler": self.get_service_info,
            "required_permission": "read"
        }
        self.methods["update_event"] = {
            "handler": self.calendar_service.update_event,
            "required_permission": "write"
        }
        
    def get_service_info(self, params, **kwargs):
        """Get information about the service implementation"""
        # Determine if we're using Google Calendar or mock implementation
        service_type = "Google Calendar" if isinstance(self.calendar_service, GoogleCalendarService) else "Mock Calendar"
        
        # Check if Google Calendar is properly authenticated
        google_auth_status = "Not applicable"
        if service_type == "Google Calendar":
            if hasattr(self.calendar_service, 'service') and self.calendar_service.service:
                google_auth_status = "Authenticated"
            else:
                google_auth_status = "Not authenticated"
        
        return {
            "service_name": "Calendar Service",
            "implementation": service_type,
            "authentication_status": google_auth_status,
            "port": 50054
        }
        self.methods["delete_event"] = {
            "handler": self.calendar_service.delete_event,
            "required_permission": "write"
        }
    
    # Include InvokeMethod, HealthCheck and DiscoverCapabilities methods same as in weather_server.py
    def InvokeMethod(self, request, context):
        # Implement just like in the original server.py, but with weather-specific methods
        # Authentication
        permissions = self.auth_provider.authenticate(request.client_id, request.api_key)
        if permissions is None:
            return pb2.MethodResponse(
                request_id=request.request_id,
                status=pb2.MethodResponse.UNAUTHORIZED,
                error_message="Authentication failed"
            )
        
        # Check if method exists
        if request.method_id not in self.methods:
            return pb2.MethodResponse(
                request_id=request.request_id,
                status=pb2.MethodResponse.NOT_FOUND,
                error_message=f"Method {request.method_id} not found"
            )
        
        method_info = self.methods[request.method_id]
        
        # Check permissions
        if not self.auth_provider.has_permission(
            request.client_id, method_info["required_permission"]
        ):
            return pb2.MethodResponse(
                request_id=request.request_id,
                status=pb2.MethodResponse.UNAUTHORIZED,
                error_message=f"Permission denied: {method_info['required_permission']} required"
            )
        
        # Execute method
        try:
            import json
            params = json.loads(request.parameters.decode("utf-8"))
            result = method_info["handler"](params, client_id=request.client_id)
            
            return pb2.MethodResponse(
                request_id=request.request_id,
                status=pb2.MethodResponse.SUCCESS,
                result=json.dumps(result).encode("utf-8")
            )
        except Exception as e:
            logging.error(f"Error executing method {request.method_id}: {str(e)}")
            return pb2.MethodResponse(
                request_id=request.request_id,
                status=pb2.MethodResponse.ERROR,
                error_message=f"Error executing method: {str(e)}"
            )
    
    def HealthCheck(self, request, context):
        return pb2.HealthCheckResponse(status=pb2.HealthCheckResponse.SERVING)
    
    def DiscoverCapabilities(self, request, context):
        # Authenticate client
        permissions = self.auth_provider.authenticate(request.client_id, request.api_key)
        if permissions is None:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Authentication failed")
        
        # Collect capabilities
        capabilities = []
        
        # Add methods
        for method_id, method_info in self.methods.items():
            if self.auth_provider.has_permission(
                request.client_id, method_info["required_permission"]
            ):
                capability = pb2.CapabilitiesResponse.Capability(
                    id=method_id,
                    name=method_id,
                    description=f"Weather API: {method_id}",
                    type=pb2.CapabilitiesResponse.Capability.METHOD,
                    required_permission=method_info["required_permission"]
                )
                capabilities.append(capability)
        
        return pb2.CapabilitiesResponse(capabilities=capabilities)

def serve(port=50054, max_workers=10):
    """Start the calendar server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    service = CalendarServer()
    
    # Register the service
    pb2_grpc.add_DistributedServiceServicer_to_server(service, server)
    
    # Start the server
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    print(f"Calendar Server started on port {port}")
    
    try:
        while True:
            time.sleep(86400)  # Sleep for a day
    except KeyboardInterrupt:
        server.stop(0)
        print("Calendar Server stopped")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    serve()