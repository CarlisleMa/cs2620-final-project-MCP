# client/multi_client.py
import grpc
import json
import hmac
import hashlib
import time
import uuid
import logging
from threading import Thread
import protocol_pb2 as pb2
import protocol_pb2_grpc as pb2_grpc

class ServerConnection:
    """Connection to a specific server"""
    def __init__(self, server_address, client_id, api_key, server_type):
        self.server_address = server_address
        self.client_id = client_id
        self.api_key = api_key
        self.server_type = server_type
        self.channel = None
        self.stub = None
        self.connected = False
        self.capabilities = {}
        
        # Connect to server
        self.connect()
    
    def connect(self):
        """Connect to the server"""
        try:
            logging.info(f"Connecting to {self.server_type} server at {self.server_address}")
            self.channel = grpc.insecure_channel(self.server_address)
            self.stub = pb2_grpc.DistributedServiceStub(self.channel)
            
            # Test connection with a health check
            response = self.stub.HealthCheck(
                pb2.HealthCheckRequest(client_id=self.client_id)
            )
            
            if response.status == pb2.HealthCheckResponse.SERVING:
                self.connected = True
                logging.info(f"Successfully connected to {self.server_type} server")
                
                # Discover capabilities
                self.discover_capabilities()
                
                return True
            else:
                logging.error(f"{self.server_type} server not serving: {response.status}")
                return False
        
        except Exception as e:
            logging.error(f"Connection error to {self.server_type} server: {str(e)}")
            self.connected = False
            return False
    
    def discover_capabilities(self):
        """Discover server capabilities"""
        try:
            response = self.stub.DiscoverCapabilities(
                pb2.DiscoverCapabilitiesRequest(client_id=self.client_id)
            )
            
            # Parse capabilities from response
            self.capabilities = {}
            for capability in response.capabilities:
                self.capabilities[capability.name] = {
                    "description": capability.description,
                    "parameters": json.loads(capability.parameters)
                }
            
            # Get service implementation info
            try:
                metadata_request = pb2.GenericRequest(
                    client_id=self.client_id,
                    params=json.dumps({"type": "service_info"})
                )
                metadata_response = self.stub.ExecuteServerMethod(
                    metadata_request, metadata=(('method', 'get_service_info'),)
                )
                self.service_info = json.loads(metadata_response.response)
                logging.info(f"{self.server_type} service info: {self.service_info}")
            except Exception as e:
                logging.warning(f"Could not get service info from {self.server_type} server: {str(e)}")
                self.service_info = {"type": "unknown"}
            
            logging.info(f"Discovered {len(self.capabilities)} capabilities on {self.server_type} server")
            return self.capabilities
        
        except Exception as e:
            logging.error(f"Error discovering capabilities on {self.server_type} server: {str(e)}")
            return {}
    
    def invoke_method(self, method_id, parameters=None, **kwargs):
        """Invoke a method on the server
        
        Args:
            method_id: The method to invoke
            parameters: Dictionary of parameters for the method
            **kwargs: Additional parameters, including client_id
            
        Returns:
            Dictionary with the method result
        """
        if not self.connected and not self.connect():
            raise Exception(f"Not connected to {self.server_type} server")
        
        if parameters is None:
            parameters = {}
        
        # Use the provided client_id if available, otherwise use the default
        client_id = kwargs.get('client_id', self.client_id)
        
        timestamp = int(time.time())
        request_id = str(uuid.uuid4())
        
        # Log whether we're using a custom client_id
        if client_id != self.client_id:
            logging.info(f"Using custom client_id '{client_id}' instead of default '{self.client_id}' for {self.server_type}.{method_id}")
        
        # Create signature
        message = f"{method_id}:{client_id}:{timestamp}"
        signature = hmac.new(
            (self.api_key or "").encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Create request
        request = pb2.MethodRequest(
            method_id=method_id,
            parameters=json.dumps(parameters).encode("utf-8"),
            request_id=request_id,
            client_id=client_id,
            api_key=self.api_key or "",
            timestamp=timestamp,
            signature=signature
        )
        
        # Send request
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
            raise Exception(f"RPC failed: {str(e)}")
    
    def close(self):
        """Close the connection to the server"""
        if self.channel:
            self.channel.close()
            self.connected = False

class MultiServerClient:
    """Client for connecting to multiple specialized servers"""
    
    def __init__(self, server_addresses, default_client_id="default_user"):
        """Initialize clients for each server type
        
        Args:
            server_addresses: Dictionary mapping server type to address
            default_client_id: Default client ID to use for all requests
        """
        self.servers = {}
        self.default_client_id = default_client_id
        
        for server_type, server_address in server_addresses.items():
            self.servers[server_type] = ServerConnection(
                server_address, self.default_client_id, None, server_type
            )
    
    def add_server(self, server_type, server_address):
        """Add a server connection"""
        self.servers[server_type] = ServerConnection(
            server_address, self.default_client_id, None, server_type
        )
        return self.servers[server_type].connected
    
    def invoke_method(self, server_type, method_id, parameters=None, client_id=None):
        """Invoke a method on a specific server
        
        Args:
            server_type: The type of server (weather, todo, calendar)
            method_id: The method to invoke
            parameters: Dictionary of parameters
            client_id: Client ID to use for this request (overrides default)
            
        Returns:
            The result of the method invocation
        """
        if parameters is None:
            parameters = {}
            
        if server_type not in self.servers:
            raise Exception(f"Server type '{server_type}' not configured")
        
        # Use the provided client_id or fall back to the default
        kwargs = {}
        if client_id is not None:
            kwargs['client_id'] = client_id
            logging.info(f"Using explicit client_id={client_id} for {server_type}.{method_id}")
        
        return self.servers[server_type].invoke_method(method_id, parameters, **kwargs)
    
    def generate_agenda(self, client_id=None):
        """Generate an agenda using data from all servers
        
        Args:
            client_id: Optional client ID to use for all requests in this agenda generation
                       If None, uses the default client ID
        """
        # If no client_id is provided, use the default
        if client_id is None:
            client_id = self.default_client_id
            
        logging.info(f"Generating agenda with client_id: {client_id}")
        
        agenda = {
            "date": time.strftime("%Y-%m-%d"),
            "weather": None,
            "events": [],
            "tasks": []
        }
        
        # Get weather for today
        if "weather" in self.servers:
            try:
                # Assuming the user is in Boston
                weather_result = self.invoke_method(
                    "weather", "get_current_weather", {"location": "Boston"}, client_id=client_id
                )
                agenda["weather"] = weather_result
            except Exception as e:
                logging.error(f"Error getting weather: {str(e)}")
        
        # Get calendar events for today
        if "calendar" in self.servers:
            try:
                # Log what type of calendar we're using
                if hasattr(self.servers["calendar"], 'service_info'):
                    service_type = self.servers["calendar"].service_info.get("implementation", "Unknown")
                    if "Google Calendar" in service_type:
                        auth_status = self.servers["calendar"].service_info.get("authentication_status", "Unknown")
                        logging.info(f"Using Google Calendar API ({auth_status}) to fetch events")
                    else:
                        logging.info(f"Using {service_type} to fetch events")
                
                logging.info("Fetching today's calendar events using system time")
                
                # Use the new get_today_events method which gets today's date from the system
                events_result = self.invoke_method(
                    "calendar", "get_today_events", {}, client_id=client_id
                )
                
                if "events" in events_result:
                    agenda["events"] = events_result["events"]
                    logging.info(f"Retrieved {len(events_result['events'])} events from calendar")
                else:
                    logging.warning("No events returned from calendar service")
            except Exception as e:
                logging.error(f"Error getting calendar events: {str(e)}")
        
        # Get todo tasks
        if "todo" in self.servers:
            try:
                logging.info(f"Retrieving tasks from todo server for client_id={client_id}")
                tasks_result = self.invoke_method(
                    "todo", "get_tasks", {}, client_id=client_id
                )
                
                logging.info(f"Retrieved {len(tasks_result.get('tasks', []))} tasks from todo server")
                
                if "tasks" in tasks_result:
                    # Sort tasks by priority
                    tasks = tasks_result["tasks"]
                    for task in tasks:
                        task["priority"] = task.get("priority", "medium")
                        
                    # Sort tasks by priority (high, medium, low)
                    priority_order = {"high": 0, "medium": 1, "low": 2}
                    tasks.sort(key=lambda x: priority_order.get(x["priority"].lower(), 99))
                    
                    agenda["tasks"] = tasks
                    logging.info(f"Sorted {len(tasks)} tasks successfully")
            except Exception as e:
                logging.error(f"Error getting tasks: {str(e)}")
        
        return agenda
    
    def close(self):
        """Close all server connections"""
        for server_type, server in self.servers.items():
            server.close()