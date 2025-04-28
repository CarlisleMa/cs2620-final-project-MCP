import json
import time
import random
import os
import hashlib
from datetime import datetime

class DistributedFunctions:
    """Real-world function handlers for the distributed system"""
    
    def __init__(self):
        # Simulated distributed database
        self.data_store = {}
        # Simulated distributed counter
        self.counters = {}
        # Simulated distributed lock system
        self.locks = {}
        # Transaction log
        self.transaction_log = []
    
    def store_data(self, params, **kwargs):
        """Store data in the distributed data store"""
        if 'key' not in params or 'value' not in params:
            return {"error": "Missing required parameters 'key' and 'value'"}
        
        key = params['key']
        value = params['value']
        
        # Simulate network latency
        time.sleep(random.uniform(0.05, 0.2))
        
        # Store the data
        self.data_store[key] = {
            'value': value,
            'timestamp': time.time(),
            'node_id': random.randint(1, 5)  # Simulate different cluster nodes
        }
        
        # Log the transaction
        self.transaction_log.append({
            'operation': 'STORE',
            'key': key,
            'timestamp': time.time(),
            'client_id': kwargs.get('client_id', 'unknown')
        })
        
        return {
            "status": "success",
            "message": f"Data stored with key '{key}'",
            "timestamp": time.time()
        }
    
    def retrieve_data(self, params, **kwargs):
        """Retrieve data from the distributed data store"""
        if 'key' not in params:
            return {"error": "Missing required parameter 'key'"}
        
        key = params['key']
        
        # Simulate network latency
        time.sleep(random.uniform(0.05, 0.2))
        
        # Retrieve the data
        if key in self.data_store:
            # Log the transaction
            self.transaction_log.append({
                'operation': 'RETRIEVE',
                'key': key,
                'timestamp': time.time(),
                'client_id': kwargs.get('client_id', 'unknown')
            })
            
            return {
                "status": "success",
                "data": self.data_store[key]['value'],
                "metadata": {
                    "timestamp": self.data_store[key]['timestamp'],
                    "node_id": self.data_store[key]['node_id']
                }
            }
        else:
            return {
                "status": "error",
                "message": f"No data found for key '{key}'"
            }
    
    def increment_counter(self, params, **kwargs):
        """Increment a distributed counter"""
        if 'counter_id' not in params:
            return {"error": "Missing required parameter 'counter_id'"}
        
        counter_id = params['counter_id']
        increment_by = params.get('increment_by', 1)
        
        # Simulate network latency and consensus delay
        time.sleep(random.uniform(0.1, 0.3))
        
        # Initialize counter if it doesn't exist
        if counter_id not in self.counters:
            self.counters[counter_id] = 0
        
        # Increment the counter
        previous_value = self.counters[counter_id]
        self.counters[counter_id] += increment_by
        
        # Log the transaction
        self.transaction_log.append({
            'operation': 'INCREMENT',
            'counter_id': counter_id,
            'previous_value': previous_value,
            'new_value': self.counters[counter_id],
            'timestamp': time.time(),
            'client_id': kwargs.get('client_id', 'unknown')
        })
        
        return {
            "status": "success",
            "counter_id": counter_id,
            "previous_value": previous_value,
            "current_value": self.counters[counter_id],
            "timestamp": time.time()
        }
    
    def acquire_lock(self, params, **kwargs):
        """Acquire a distributed lock"""
        if 'resource_id' not in params:
            return {"error": "Missing required parameter 'resource_id'"}
        
        resource_id = params['resource_id']
        timeout = params.get('timeout', 5.0)  # Default timeout of 5 seconds
        client_id = kwargs.get('client_id', 'unknown')
        
        start_time = time.time()
        
        # Try to acquire the lock
        while time.time() - start_time < timeout:
            # Check if the lock is available
            if resource_id not in self.locks or (
                time.time() - self.locks[resource_id]['timestamp'] > 
                self.locks[resource_id]['ttl']
            ):
                # Lock is available, acquire it
                lock_id = hashlib.md5(f"{resource_id}:{time.time()}:{client_id}".encode()).hexdigest()
                ttl = params.get('ttl', 30.0)  # Default TTL of 30 seconds
                
                self.locks[resource_id] = {
                    'lock_id': lock_id,
                    'client_id': client_id,
                    'timestamp': time.time(),
                    'ttl': ttl
                }
                
                # Log the transaction
                self.transaction_log.append({
                    'operation': 'LOCK_ACQUIRE',
                    'resource_id': resource_id,
                    'lock_id': lock_id,
                    'timestamp': time.time(),
                    'client_id': client_id
                })
                
                return {
                    "status": "success",
                    "resource_id": resource_id,
                    "lock_id": lock_id,
                    "ttl": ttl,
                    "acquired_at": time.time()
                }
            
            # Lock is not available, wait and retry
            time.sleep(0.2)
        
        # Timeout reached, could not acquire lock
        return {
            "status": "error",
            "message": f"Could not acquire lock for resource '{resource_id}' within timeout period",
            "current_owner": self.locks.get(resource_id, {}).get('client_id')
        }
    
    def release_lock(self, params, **kwargs):
        """Release a distributed lock"""
        if 'resource_id' not in params or 'lock_id' not in params:
            return {"error": "Missing required parameters 'resource_id' and 'lock_id'"}
        
        resource_id = params['resource_id']
        lock_id = params['lock_id']
        client_id = kwargs.get('client_id', 'unknown')
        
        # Check if the lock exists
        if resource_id not in self.locks:
            return {
                "status": "error",
                "message": f"No lock found for resource '{resource_id}'"
            }
        
        # Check if the lock ID matches
        if self.locks[resource_id]['lock_id'] != lock_id:
            return {
                "status": "error",
                "message": f"Invalid lock ID for resource '{resource_id}'"
            }
        
        # Check if the client ID matches (only the lock owner can release it)
        if self.locks[resource_id]['client_id'] != client_id:
            return {
                "status": "error",
                "message": f"Only the lock owner can release the lock for resource '{resource_id}'"
            }
        
        # Release the lock
        del self.locks[resource_id]
        
        # Log the transaction
        self.transaction_log.append({
            'operation': 'LOCK_RELEASE',
            'resource_id': resource_id,
            'lock_id': lock_id,
            'timestamp': time.time(),
            'client_id': client_id
        })
        
        return {
            "status": "success",
            "message": f"Lock released for resource '{resource_id}'",
            "timestamp": time.time()
        }
    
    def get_transaction_log(self, params, **kwargs):
        """Get the transaction log"""
        limit = params.get('limit', 10)
        offset = params.get('offset', 0)
        
        # Retrieve the logs with pagination
        logs = self.transaction_log[offset:offset+limit]
        total_logs = len(self.transaction_log)
        
        return {
            "status": "success",
            "logs": logs,
            "pagination": {
                "total": total_logs,
                "offset": offset,
                "limit": limit,
                "has_more": (offset + limit) < total_logs
            }
        }