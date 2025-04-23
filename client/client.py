# client/client.py
import grpc
import json
import hmac
import hashlib
import time
import uuid
import logging
from threading import Thread

# Import the generated protocol buffer code
import protocol_pb2 as pb2
import protocol_pb2_grpc as pb2_grpc

class CircuitBreaker:
    """Circuit breaker for fault tolerance"""
    def __init__(self, failure_threshold=5, reset_timeout=30):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = 0
    
    def execute(self, func, *args, **kwargs):
        """Execute function with circuit breaker pattern"""
        if self.state == "OPEN":
            # Check if timeout has elapsed to try again
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset if in HALF_OPEN
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            
            return result
        
        except Exception as e:
            # Record failure
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # Check if threshold reached
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise e

class DistributedClient:
    """Client for the Enhanced MCP protocol"""
    def __init__(self, server_address, client_id, api_key, reconnect_attempts=5):
        self.server_address = server_address
        self.client_id = client_id
        self.api_key = api_key
        self.reconnect_attempts = reconnect_attempts
        self.logger = logging.getLogger("distributed_client")
        
        # Connection setup
        self.channel = None
        self.stub = None
        self.connected = False
        
        # Event handling
        self.event_handlers = {}
        self.event_listener_thread = None
        
        # Circuit breaker for fault tolerance
        self.circuit_breaker = CircuitBreaker()
        
        # Discovered capabilities
        self.capabilities = {}
        
        # Connect to server
        self.connect()
    
    def connect(self):
        """Connect to the server"""
        try:
            self.logger.info(f"Connecting to server at {self.server_address}")
            self.channel = grpc.insecure_channel(self.server_address)
            self.stub = pb2_grpc.DistributedServiceStub(self.channel)
            
            # Test connection with a health check
            response = self.stub.HealthCheck(
                pb2.HealthCheckRequest(client_id=self.client_id)
            )
            
            if response.status == pb2.HealthCheckResponse.SERVING:
                self.connected = True
                self.logger.info("Successfully connected to server")
                
                # Discover capabilities
                self.discover_capabilities()
                
                return True
            else:
                self.logger.error(f"Server not serving: {response.status}")
                return False
        
        except Exception as e:
            self.logger.error(f"Connection error: {str(e)}")
            self.connected = False
            return False
    
    def reconnect(self):
        """Attempt to reconnect to the server"""
        self.connected = False
        
        for attempt in range(self.reconnect_attempts):
            self.logger.info(f"Reconnection attempt {attempt + 1}/{self.reconnect_attempts}")
            
            if self.connect():
                return True
            
            # Exponential backoff with jitter
            backoff = min(2 ** attempt, 60)  # Max 60 seconds
            jitter = backoff * 0.1 * (2 * (0.5 - 0.5))  # ±10% jitter
            sleep_time = backoff + jitter
            
            self.logger.info(f"Reconnection failed, waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.logger.error("Failed to reconnect after maximum attempts")
        return False
    
    def discover_capabilities(self):
        """Discover server capabilities"""
        try:
            self.logger.info("Discovering server capabilities")
            
            response = self.stub.DiscoverCapabilities(
                pb2.DiscoveryRequest(
                    client_id=self.client_id,
                    api_key=self.api_key
                )
            )
            
            # Process capabilities
            self.capabilities = {}
            for capability in response.capabilities:
                self.capabilities[capability.id] = {
                    "name": capability.name,
                    "description": capability.description,
                    "type": capability.type,
                    "required_permission": capability.required_permission
                }
            
            self.logger.info(f"Discovered {len(self.capabilities)} capabilities")
            return self.capabilities
        
        except Exception as e:
            self.logger.error(f"Error discovering capabilities: {str(e)}")
            return {}
    
    def _create_signature(self, method_id, timestamp):
        """Create HMAC signature for request authentication"""
        message = f"{method_id}:{self.client_id}:{timestamp}"
        signature = hmac.new(
            self.api_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def invoke_method(self, method_id, parameters=None):
        """Invoke a method on the server"""
        if not self.connected and not self.reconnect():
            raise Exception("Not connected to server")
        
        if parameters is None:
            parameters = {}
        
        timestamp = int(time.time())
        request_id = str(uuid.uuid4())
        
        # Create request
        request = pb2.MethodRequest(
            method_id=method_id,
            parameters=json.dumps(parameters).encode("utf-8"),
            request_id=request_id,
            client_id=self.client_id,
            api_key=self.api_key,
            timestamp=timestamp,
            signature=self._create_signature(method_id, timestamp)
        )
        
        # Use circuit breaker for fault tolerance
        try:
            return self.circuit_breaker.execute(self._send_method_request, request)
        except Exception as e:
            self.logger.error(f"Method invocation failed: {str(e)}")
            raise e
    
    def _send_method_request(self, request):
        """Send method request with retry logic"""
        try:
            response = self.stub.InvokeMethod(request)
            
            if response.status == pb2.MethodResponse.SUCCESS:
                result = json.loads(response.result.decode("utf-8"))
                return result
            else:
                error_message = response.error_message or f"Error status: {response.status}"
                raise Exception(error_message)
        
        except grpc.RpcError as e:
            self.connected = False
            
            # Try to reconnect
            if self.reconnect():
                # Retry the request
                response = self.stub.InvokeMethod(request)
                
                if response.status == pb2.MethodResponse.SUCCESS:
                    result = json.loads(response.result.decode("utf-8"))
                    return result
                else:
                    error_message = response.error_message or f"Error status: {response.status}"
                    raise Exception(error_message)
            else:
                raise Exception(f"RPC failed: {str(e)}")
    
    def subscribe_to_events(self, pattern, handler):
        """Subscribe to events matching the given pattern"""
        if not self.connected and not self.reconnect():
            raise Exception("Not connected to server")
        
        self.event_handlers[pattern] = handler
        
        # Start event listener if not already running
        if self.event_listener_thread is None or not self.event_listener_thread.is_alive():
            self.event_listener_thread = Thread(target=self._event_listener_loop)
            self.event_listener_thread.daemon = True
            self.event_listener_thread.start()
    
    def _event_listener_loop(self):
        """Background thread for handling event subscriptions"""
        subscription_id = str(uuid.uuid4())
        
        request = pb2.EventSubscription(
            client_id=self.client_id,
            api_key=self.api_key,
            pattern="*",  # Subscribe to all events and filter locally
            subscription_id=subscription_id
        )
        
        while self.connected:
            try:
                # Start event stream
                for event in self.stub.SubscribeToEvents(request):
                    event_type = event.event_type
                    event_data = json.loads(event.data.decode("utf-8"))
                    
                    # Find matching handlers
                    for pattern, handler in self.event_handlers.items():
                        if self._pattern_matches(event_type, pattern):
                            try:
                                handler(event_type, event_data)
                            except Exception as e:
                                self.logger.error(
                                    f"Error in event handler for {event_type}: {str(e)}"
                                )
            
            except grpc.RpcError as e:
                self.logger.error(f"Event subscription error: {str(e)}")
                self.connected = False
                
                # Try to reconnect
                if self.reconnect():
                    continue
                else:
                    break
            
            except Exception as e:
                self.logger.error(f"Unexpected error in event listener: {str(e)}")
                time.sleep(5)  # Avoid rapid reconnection attempts
    
    def _pattern_matches(self, event_type, pattern):
        """Check if an event type matches a subscription pattern"""
        if pattern == "*":
            return True
        
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return event_type.startswith(prefix)
        
        return event_type == pattern
    
    def close(self):
        """Close the connection to the server"""
        if self.channel:
            self.channel.close()
            self.connected = False
            self.logger.info("Connection closed")

# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    client = DistributedClient(
        server_address="localhost:50051",
        client_id="client1",
        api_key="sk_client1_12345abcde"
    )
    
    try:
        # Invoke methods
        result = client.invoke_method("add", {"a": 5, "b": 3})
        print(f"5 + 3 = {result['result']}")
        
        result = client.invoke_method("multiply", {"a": 5, "b": 3})
        print(f"5 * 3 = {result['result']}")
        
        # Subscribe to events
        def event_handler(event_type, data):
            print(f"Received event {event_type}: {data}")
        
        client.subscribe_to_events("system.*", event_handler)
        
        # Keep running to receive events
        print("Listening for events (press Ctrl+C to exit)...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    finally:
        client.close()