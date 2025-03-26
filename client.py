import socket
import json
import threading
import logging
import time
from typing import Dict, Any, Callable, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("Fusion360_MCP_Client")

class MCPClient:
    """
    Client for interacting with the Master Control Program server for Fusion 360
    """
    
    def __init__(self, host: str = '127.0.0.1', port: int = 8080):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.running = False
        self.response_handlers: Dict[str, Callable] = {}
        self.receive_thread = None
    
    def connect(self) -> bool:
        """Connect to the MCP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.running = True
            
            # Start the receive thread
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            logger.info(f"Connected to MCP server at {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the MCP server"""
        self.running = False
        self.connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            
        logger.info("Disconnected from MCP server")
    
    def receive_messages(self):
        """Receive and process messages from the server"""
        while self.running and self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    logger.warning("Connection to MCP server closed")
                    self.connected = False
                    break
                
                # Process the received data
                response = json.loads(data.decode('utf-8'))
                self.handle_response(response)
                
            except Exception as e:
                if self.running:
                    logger.error(f"Error receiving message: {e}")
                    self.connected = False
                break
    
    def handle_response(self, response: Dict[str, Any]):
        """Handle a response from the server"""
        if 'type' not in response:
            logger.warning(f"Received response without type: {response}")
            return
            
        response_type = response['type']
        logger.info(f"Received {response_type} response")
        
        # Call the appropriate handler if registered
        if response_type in self.response_handlers:
            try:
                self.response_handlers[response_type](response)
            except Exception as e:
                logger.error(f"Error in response handler for {response_type}: {e}")
    
    def register_handler(self, response_type: str, handler: Callable):
        """Register a handler for a specific response type"""
        self.response_handlers[response_type] = handler
        logger.info(f"Registered handler for {response_type} responses")
    
    def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a message to the MCP server"""
        if not self.connected:
            logger.error("Cannot send message: Not connected to server")
            return False
            
        try:
            data = json.dumps(message).encode('utf-8')
            self.socket.sendall(data)
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.connected = False
            return False
    
    def execute_fusion_command(self, command: str, params: Dict[str, Any] = None) -> bool:
        """Execute a command in Fusion 360 via the MCP server"""
        if params is None:
            params = {}
            
        message = {
            'type': 'fusion_command',
            'command': command,
            'params': params
        }
        
        return self.send_message(message)
    
    def get_model_info(self) -> bool:
        """Request model information from the MCP server"""
        message = {
            'type': 'get_model_info'
        }
        
        return self.send_message(message)


# Example usage
if __name__ == "__main__":
    # Create and connect the client
    client = MCPClient()
    
    if client.connect():
        try:
            # Register response handlers
            def command_result_handler(response):
                result = response.get('result', {})
                print(f"Command result: {result}")
            
            def model_info_handler(response):
                model_info = response.get('data', {})
                print(f"Model info: {model_info}")
            
            client.register_handler('command_result', command_result_handler)
            client.register_handler('model_info', model_info_handler)
            
            # Example: Get model info
            client.get_model_info()
            
            # Example: Execute a command
            client.execute_fusion_command('create_circle', {
                'center': [0, 0, 0],
                'radius': 10
            })
            
            # Keep the client running for a while to receive responses
            time.sleep(5)
            
        finally:
            client.disconnect()
    else:
        print("Failed to connect to MCP server. Make sure it's running.") 