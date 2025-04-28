import re
import json
import random
import time

class MockLlmAgent:
    """Simulates an LLM agent that can understand natural language and call methods"""
    
    def __init__(self, client):
        self.client = client
        self.conversation_history = []
        
        # Define patterns for recognizing intents
        self.patterns = {
            'store_data': r'store\s+(?:the\s+)?(?:value|data)\s+(?P<value>[^"]+|"[^"]+")(?:\s+with(?:\s+the)?\s+key\s+|\s+as\s+)(?P<key>[^"]+|"[^"]+")',
            'retrieve_data': r'(?:get|retrieve|fetch)(?:\s+the)?(?:\s+value|\s+data)?\s+(?:for|with)(?:\s+the)?\s+key\s+(?P<key>[^"]+|"[^"]+")',
            'increment_counter': r'increment(?:\s+the)?\s+counter\s+(?P<counter_id>[^"]+|"[^"]+")(?:\s+by\s+(?P<increment_by>\d+))?',
            'acquire_lock': r'(?:acquire|get|obtain)(?:\s+a)?\s+lock\s+(?:for|on)(?:\s+the)?\s+resource\s+(?P<resource_id>[^"]+|"[^"]+")(?:\s+with(?:\s+a)?\s+timeout\s+of\s+(?P<timeout>\d+))?(?:\s+(?:seconds|s))?',
            'release_lock': r'release(?:\s+the)?\s+lock\s+(?P<lock_id>[^"]+|"[^"]+")(?:\s+for(?:\s+the)?\s+resource\s+(?P<resource_id>[^"]+|"[^"]+"))?',
            'transaction_log': r'(?:get|show|display)(?:\s+the)?\s+(?:transaction|event)(?:\s+log|\s+history)',
        }
    
    def _extract_quoted_or_word(self, text):
        """Extract a value that might be quoted or a single word"""
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        return text
    
    def process_message(self, message):
        """Process a natural language message and convert it to a method call"""
        self.conversation_history.append({"role": "user", "content": message})
        
        # Try to match the message against known patterns
        for intent, pattern in self.patterns.items():
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                # Extract parameters from the match
                params = {k: self._extract_quoted_or_word(v) for k, v in match.groupdict().items() if v is not None}
                
                # Convert numeric values
                for key, value in params.items():
                    if re.match(r'^\d+$', value):
                        params[key] = int(value)
                    elif re.match(r'^\d+\.\d+$', value):
                        params[key] = float(value)
                
                # Call the appropriate method
                try:
                    if intent == 'store_data':
                        result = self.client.invoke_method('store_data', params)
                    elif intent == 'retrieve_data':
                        result = self.client.invoke_method('retrieve_data', params)
                    elif intent == 'increment_counter':
                        result = self.client.invoke_method('increment_counter', params)
                    elif intent == 'acquire_lock':
                        result = self.client.invoke_method('acquire_lock', params)
                    elif intent == 'release_lock':
                        result = self.client.invoke_method('release_lock', params)
                    elif intent == 'transaction_log':
                        result = self.client.invoke_method('get_transaction_log', params)
                    
                    response = self._generate_response(intent, result)
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
                except Exception as e:
                    error_response = f"I encountered an error while trying to {intent.replace('_', ' ')}: {str(e)}"
                    self.conversation_history.append({"role": "assistant", "content": error_response})
                    return error_response
        
        # No pattern matched, return a fallback response
        fallback = "I'm not sure how to process that request. You can ask me to store data, retrieve data, increment a counter, acquire or release locks, or view the transaction log."
        self.conversation_history.append({"role": "assistant", "content": fallback})
        return fallback
    
    def _generate_response(self, intent, result):
        """Generate a natural language response based on the method result"""
        if intent == 'store_data':
            if result.get('status') == 'success':
                return f"I've stored the data successfully. {result.get('message', '')}"
            else:
                return f"I couldn't store the data. {result.get('error', 'An unknown error occurred.')}"
        
        elif intent == 'retrieve_data':
            if result.get('status') == 'success':
                value = result.get('data', 'No data')
                return f"Here's the data I retrieved: {value}"
            else:
                return f"I couldn't retrieve the data. {result.get('message', 'An unknown error occurred.')}"
        
        elif intent == 'increment_counter':
            if result.get('status') == 'success':
                counter_id = result.get('counter_id')
                current_value = result.get('current_value')
                previous_value = result.get('previous_value')
                return f"I've incremented the counter '{counter_id}' from {previous_value} to {current_value}."
            else:
                return f"I couldn't increment the counter. {result.get('error', 'An unknown error occurred.')}"
        
        elif intent == 'acquire_lock':
            if result.get('status') == 'success':
                resource_id = result.get('resource_id')
                lock_id = result.get('lock_id')
                ttl = result.get('ttl')
                return f"I've acquired a lock for resource '{resource_id}'. The lock ID is '{lock_id}' and it will expire in {ttl} seconds if not released."
            else:
                return f"I couldn't acquire the lock. {result.get('message', 'An unknown error occurred.')}"
        
        elif intent == 'release_lock':
            if result.get('status') == 'success':
                return f"I've released the lock successfully. {result.get('message', '')}"
            else:
                return f"I couldn't release the lock. {result.get('message', 'An unknown error occurred.')}"
        
        elif intent == 'transaction_log':
            if result.get('status') == 'success':
                logs = result.get('logs', [])
                if not logs:
                    return "The transaction log is empty."
                
                log_summary = "\n\n".join([
                    f"Operation: {log.get('operation')}\n"
                    f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(log.get('timestamp')))}\n"
                    f"Client: {log.get('client_id')}\n"
                    f"Details: {', '.join([f'{k}: {v}' for k, v in log.items() if k not in ['operation', 'timestamp', 'client_id']])}"
                    for log in logs
                ])
                
                pagination = result.get('pagination', {})
                total = pagination.get('total', 0)
                has_more = pagination.get('has_more', False)
                
                footer = f"\nShowing {len(logs)} of {total} transactions."
                if has_more:
                    footer += " There are more transactions available."
                
                return f"Here's the transaction log:\n\n{log_summary}\n{footer}"
            else:
                return f"I couldn't retrieve the transaction log. {result.get('error', 'An unknown error occurred.')}"
        
        # Default response for unknown intents
        return f"Operation completed with result: {json.dumps(result, indent=2)}"