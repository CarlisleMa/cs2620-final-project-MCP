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
            
            logging.info(f"Discovered {len(self.capabilities)} capabilities on {self.server_type} server")
            return self.capabilities
        
        except Exception as e:
            logging.error(f"Error discovering capabilities on {self.server_type} server: {str(e)}")
            return {}
    
    def invoke_method(self, method_id, parameters=None):
        """Invoke a method on the server"""
        if not self.connected and not self.connect():
            raise Exception(f"Not connected to {self.server_type} server")
        
        if parameters is None:
            parameters = {}
        
        timestamp = int(time.time())
        request_id = str(uuid.uuid4())
        
        # Create signature
        message = f"{method_id}:{self.client_id}:{timestamp}"
        signature = hmac.new(
            self.api_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Create request
        request = pb2.MethodRequest(
            method_id=method_id,
            parameters=json.dumps(parameters).encode("utf-8"),
            request_id=request_id,
            client_id=self.client_id,
            api_key=self.api_key,
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
    """Client that can connect to multiple specialized servers"""
    def __init__(self, client_id, api_key):
        self.client_id = client_id
        self.api_key = api_key
        self.servers = {}
    
    def add_server(self, server_type, server_address):
        """Add a server connection"""
        self.servers[server_type] = ServerConnection(
            server_address, self.client_id, self.api_key, server_type
        )
        return self.servers[server_type].connected
    
    def invoke_method(self, server_type, method_id, parameters=None):
        """Invoke a method on a specific server"""
        if server_type not in self.servers:
            raise Exception(f"Server type '{server_type}' not configured")
        
        return self.servers[server_type].invoke_method(method_id, parameters)
    
    def generate_agenda(self):
        """Generate an agenda using data from all servers"""
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
                weather_result = self.servers["weather"].invoke_method(
                    "get_current_weather", {"location": "Boston"}
                )
                agenda["weather"] = weather_result
            except Exception as e:
                logging.error(f"Error getting weather: {str(e)}")
        
        # Get calendar events for today
        if "calendar" in self.servers:
            try:
                today = time.strftime("%Y-%m-%d")
                tomorrow = time.strftime(
                    "%Y-%m-%d", time.localtime(time.time() + 86400)
                )
                
                events_result = self.servers["calendar"].invoke_method(
                    "get_events",
                    {"start_date": today, "end_date": tomorrow}
                )
                
                if "events" in events_result:
                    agenda["events"] = events_result["events"]
            except Exception as e:
                logging.error(f"Error getting calendar events: {str(e)}")
        
        # Get todo tasks
        if "todo" in self.servers:
            try:
                tasks_result = self.servers["todo"].invoke_method(
                    "get_tasks", {"include_completed": False}
                )
                
                if "tasks" in tasks_result:
                    agenda["tasks"] = tasks_result["tasks"]
            except Exception as e:
                logging.error(f"Error getting tasks: {str(e)}")
        
        return agenda
    
    def close(self):
        """Close all server connections"""
        for server_type, server in self.servers.items():
            server.close()