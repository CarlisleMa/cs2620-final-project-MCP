# server/server.py
import grpc
import json
import time
import logging
import uuid
from concurrent import futures

# Import the generated protocol buffer code
import enhanced_mcp_pb2 as pb2
import enhanced_mcp_pb2_grpc as pb2_grpc

from server.auth_provider import AuthProvider

class DistributedServer(pb2_grpc.DistributedServiceServicer):
    def __init__(self):
        self.methods = {}
        self.resources = {}
        self.event_subscribers = {}
        self.auth_provider = AuthProvider()
        self.logger = logging.getLogger("distributed_server")
        
        # Register built-in methods
        self._register_builtin_methods()
    
    def register_method(self, method_id, handler, required_permission="read"):
        """Register a method that clients can invoke"""
        self.methods[method_id] = {
            "handler": handler,
            "required_permission": required_permission
        }
        self.logger.info(f"Registered method: {method_id}")
    
    def register_resource(self, resource_id, resource, required_permission="read"):
        """Register a resource that clients can access"""
        self.resources[resource_id] = {
            "data": resource,
            "required_permission": required_permission
        }
        self.logger.info(f"Registered resource: {resource_id}")
    
    def _register_builtin_methods(self):
        """Register built-in methods available to all clients"""
        self.register_method("ping", self._handle_ping)
        self.register_method("echo", self._handle_echo)
    
    def _handle_ping(self, params, **kwargs):
        """Handle the built-in ping method"""
        return {"timestamp": time.time(), "status": "ok"}
    
    def _handle_echo(self, params, **kwargs):
        """Handle the built-in echo method"""
        return params
    
    def InvokeMethod(self, request, context):
        """Implement the InvokeMethod RPC method"""
        self.logger.info(f"Method invocation request: {request.method_id} from {request.client_id}")
        
        # Authenticate client
        permissions = self.auth_provider.authenticate(request.client_id, request.api_key)
        if permissions is None:
            self.logger.warning(f"Authentication failed for client {request.client_id}")
            return pb2.MethodResponse(
                request_id=request.request_id,
                status=pb2.MethodResponse.UNAUTHORIZED,
                error_message="Authentication failed"
            )
        
        # Validate signature
        if not self.auth_provider.validate_signature(
            request.client_id, request.method_id, request.timestamp, request.signature
        ):
            self.logger.warning(f"Signature validation failed for client {request.client_id}")
            return pb2.MethodResponse(
                request_id=request.request_id,
                status=pb2.MethodResponse.UNAUTHORIZED,
                error_message="Invalid request signature"
            )
        
        # Check if method exists
        if request.method_id not in self.methods:
            self.logger.warning(f"Method not found: {request.method_id}")
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
            self.logger.warning(
                f"Permission denied for client {request.client_id}: "
                f"requires {method_info['required_permission']}"
            )
            return pb2.MethodResponse(
                request_id=request.request_id,
                status=pb2.MethodResponse.UNAUTHORIZED,
                error_message=f"Permission denied: {method_info['required_permission']} required"
            )
        
        # Execute method
        try:
            params = json.loads(request.parameters.decode("utf-8"))
            result = method_info["handler"](params, client_id=request.client_id)
            
            return pb2.MethodResponse(
                request_id=request.request_id,
                status=pb2.MethodResponse.SUCCESS,
                result=json.dumps(result).encode("utf-8")
            )
        except Exception as e:
            self.logger.error(f"Error executing method {request.method_id}: {str(e)}")
            return pb2.MethodResponse(
                request_id=request.request_id,
                status=pb2.MethodResponse.ERROR,
                error_message=f"Error executing method: {str(e)}"
            )
    
    def HealthCheck(self, request, context):
        """Implement the HealthCheck RPC method"""
        # Simple health check - just return SERVING status
        return pb2.HealthCheckResponse(status=pb2.HealthCheckResponse.SERVING)
    
    def DiscoverCapabilities(self, request, context):
        """Implement the DiscoverCapabilities RPC method"""
        # Authenticate client
        permissions = self.auth_provider.authenticate(request.client_id, request.api_key)
        if permissions is None:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Authentication failed")
        
        # Collect capabilities
        capabilities = []
        
        # Add methods
        for method_id, method_info in self.methods.items():
            # Only include methods the client has permission to access
            if self.auth_provider.has_permission(
                request.client_id, method_info["required_permission"]
            ):
                capability = pb2.CapabilitiesResponse.Capability(
                    id=method_id,
                    name=method_id,  # Could be different than ID
                    description=f"Method: {method_id}",
                    type=pb2.CapabilitiesResponse.Capability.METHOD,
                    required_permission=method_info["required_permission"]
                )
                capabilities.append(capability)
        
        # Add resources
        for resource_id, resource_info in self.resources.items():
            if self.auth_provider.has_permission(
                request.client_id, resource_info["required_permission"]
            ):
                capability = pb2.CapabilitiesResponse.Capability(
                    id=resource_id,
                    name=resource_id,
                    description=f"Resource: {resource_id}",
                    type=pb2.CapabilitiesResponse.Capability.RESOURCE,
                    required_permission=resource_info["required_permission"]
                )
                capabilities.append(capability)
        
        return pb2.CapabilitiesResponse(capabilities=capabilities)
    
    def SubscribeToEvents(self, request, context):
        """Implement the SubscribeToEvents RPC method"""
        # Authenticate client
        permissions = self.auth_provider.authenticate(request.client_id, request.api_key)
        if permissions is None:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Authentication failed")
        
        # Check subscription permission
        if not self.auth_provider.has_permission(request.client_id, "subscribe"):
            context.abort(
                grpc.StatusCode.PERMISSION_DENIED, 
                "Permission denied: 'subscribe' permission required"
            )
        
        # Register subscription
        subscription_id = request.subscription_id or str(uuid.uuid4())
        self.event_subscribers[subscription_id] = {
            "client_id": request.client_id,
            "pattern": request.pattern,
            "context": context
        }
        
        self.logger.info(f"New event subscription: {subscription_id} from {request.client_id}")
        
        # Keep the connection open and send events as they occur
        try:
            while context.is_active():
                # In a real implementation, this would wait for events
                # For now, just sleep to keep the connection open
                time.sleep(10)
        finally:
            # Clean up subscription when client disconnects
            if subscription_id in self.event_subscribers:
                del self.event_subscribers[subscription_id]
                self.logger.info(f"Subscription ended: {subscription_id}")
    
    def broadcast_event(self, event_type, data):
        """Broadcast an event to all subscribed clients"""
        event_id = str(uuid.uuid4())
        event = pb2.EventNotification(
            event_id=event_id,
            event_type=event_type,
            data=json.dumps(data).encode("utf-8"),
            timestamp=int(time.time())
        )
        
        for subscription_id, subscription in list(self.event_subscribers.items()):
            try:
                pattern = subscription["pattern"]
                
                # Check if the event matches the subscription pattern
                if self._pattern_matches(event_type, pattern):
                    # Check if the client is still connected
                    if subscription["context"].is_active():
                        subscription["context"].write(event)
                        self.logger.info(
                            f"Event {event_id} sent to subscription {subscription_id}"
                        )
                    else:
                        # Clean up inactive subscription
                        del self.event_subscribers[subscription_id]
                        self.logger.info(
                            f"Removed inactive subscription: {subscription_id}"
                        )
            except Exception as e:
                self.logger.error(
                    f"Error broadcasting event to subscription {subscription_id}: {str(e)}"
                )
                # Clean up subscription with error
                if subscription_id in self.event_subscribers:
                    del self.event_subscribers[subscription_id]
    
    def _pattern_matches(self, event_type, pattern):
        """Check if an event type matches a subscription pattern"""
        if pattern == "*":
            return True
        
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return event_type.startswith(prefix)
        
        return event_type == pattern

def serve(port=50051, max_workers=10):
    """Start the gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    service = DistributedServer()
    
    # Register some example methods
    service.register_method("add", lambda params, **kwargs: {
        "result": params.get("a", 0) + params.get("b", 0)
    })
    
    service.register_method("multiply", lambda params, **kwargs: {
        "result": params.get("a", 0) * params.get("b", 0)
    }, required_permission="write")
    
    # Register the service
    pb2_grpc.add_DistributedServiceServicer_to_server(service, server)
    
    # Start the server
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    print(f"Server started on port {port}")
    
    # Keep the server running
    try:
        while True:
            time.sleep(86400)  # Sleep for a day
    except KeyboardInterrupt:
        server.stop(0)
        print("Server stopped")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    serve()