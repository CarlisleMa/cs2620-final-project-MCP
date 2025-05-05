import grpc
import time
import logging
from concurrent import futures
import protocol_pb2 as pb2
import protocol_pb2_grpc as pb2_grpc
from server.auth_provider import AuthProvider
from server.weather_service import WeatherService

class WeatherServer(pb2_grpc.DistributedServiceServicer):
    def __init__(self):
        self.methods = {}
        self.auth_provider = AuthProvider()
        self.weather_service = WeatherService()
        self.register_methods()
        
    def register_methods(self):
        self.methods["get_current_weather"] = {
            "handler": self.weather_service.get_current_weather,
            "required_permission": "read"
        }
        self.methods["get_forecast"] = {
            "handler": self.weather_service.get_forecast,
            "required_permission": "read"
        }
        self.methods["get_service_info"] = {
            "handler": self.get_service_info,
            "required_permission": "read"
        }
        
    def get_service_info(self, params, **kwargs):
        """Get information about the service implementation"""
        # Check if using real weather API or mock
        service_type = "WeatherAPI.com" if self.weather_service.api_key else "Mock Weather"
        
        return {
            "service_name": "Weather Service", 
            "implementation": service_type,
            "api_key_configured": bool(self.weather_service.api_key),
            "port": 50052
        }
    
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

def serve(port=50052, max_workers=10):
    """Start the weather server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    service = WeatherServer()
    
    # Register the service
    pb2_grpc.add_DistributedServiceServicer_to_server(service, server)
    
    # Start the server
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    print(f"Weather Server started on port {port}")
    
    try:
        while True:
            time.sleep(86400)  # Sleep for a day
    except KeyboardInterrupt:
        server.stop(0)
        print("Weather Server stopped")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    serve()