import grpc
import time
import logging
from concurrent import futures
import protocol_pb2 as pb2
import protocol_pb2_grpc as pb2_grpc
from server.auth_provider import AuthProvider
from server.todo_service import TodoService

class TodoServer(pb2_grpc.DistributedServiceServicer):
    def __init__(self):
        self.methods = {}
        self.auth_provider = AuthProvider()
        self.todo_service = TodoService()
        self.register_methods()
        
    def register_methods(self):
        self.methods["add_task"] = {
            "handler": self.todo_service.add_task,
            "required_permission": "write"
        }
        self.methods["get_tasks"] = {
            "handler": self.todo_service.get_tasks,
            "required_permission": "read"
        }
        self.methods["update_task"] = {
            "handler": self.todo_service.update_task,
            "required_permission": "write"
        }
        self.methods["delete_task"] = {
            "handler": self.todo_service.delete_task,
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

def serve(port=50053, max_workers=10):
    """Start the todo server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    service = TodoServer()
    
    # Register the service
    pb2_grpc.add_DistributedServiceServicer_to_server(service, server)
    
    # Start the server
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    print(f"Todo Server started on port {port}")
    
    try:
        while True:
            time.sleep(86400)  # Sleep for a day
    except KeyboardInterrupt:
        server.stop(0)
        print("Todo Server stopped")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    serve()