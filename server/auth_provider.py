# server/auth_provider.py
import hmac
import hashlib
import time
import logging

class AuthProvider:
    def __init__(self):
        # In a real system, keys would be securely stored
        self.api_keys = {
            "client1": {
                "key": "sk_client1_12345abcde", 
                "permissions": ["read", "write", "subscribe"]
            },
            "client2": {
                "key": "sk_client2_67890fghij", 
                "permissions": ["read"]
            }
        }
        self.logger = logging.getLogger("auth_provider")
    
    def authenticate(self, client_id, api_key):
        """Validate API key and return permissions if valid"""
        if client_id in self.api_keys and self.api_keys[client_id]["key"] == api_key:
            self.logger.info(f"Client {client_id} authenticated successfully")
            return self.api_keys[client_id]["permissions"]
        
        self.logger.warning(f"Authentication failed for client {client_id}")
        return None
    
    def validate_signature(self, client_id, method_id, timestamp, signature):
        """Validate request signature"""
        if client_id not in self.api_keys:
            return False
        
        # Check if timestamp is within acceptable range (5 minutes)
        current_time = int(time.time())
        if abs(current_time - timestamp) > 300:  # 5 minutes
            self.logger.warning(f"Signature timestamp expired for client {client_id}")
            return False
        
        # Recreate the signature
        api_key = self.api_keys[client_id]["key"]
        message = f"{method_id}:{client_id}:{timestamp}"
        expected_signature = hmac.new(
            api_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        is_valid = signature == expected_signature
        if not is_valid:
            self.logger.warning(f"Invalid signature for client {client_id}")
        
        return is_valid
    
    def has_permission(self, client_id, required_permission):
        """Check if client has the required permission"""
        if client_id not in self.api_keys:
            return False
        
        return required_permission in self.api_keys[client_id]["permissions"]