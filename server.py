import socket
import threading
import json
import logging
import os
import time
from typing import Dict, Any, List, Optional

try:
    import openai
except ImportError:  # pragma: no cover - optional dependency
    openai = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("Fusion360_MCP")

class MCPServer:
    """
    Master Control Program server for Fusion 360
    Handles communication between clients and Fusion 360
    """
    
    def __init__(self, host: str = '127.0.0.1', port: int = 8080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients: Dict[str, socket.socket] = {}
        self.fusion_data: Dict[str, Any] = {}
        self.running = False
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
    
    def start(self):
        """Start the MCP server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            logger.info(f"MCP Server started on {self.host}:{self.port}")
            
            # Start accepting client connections
            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
            # Main server loop
            try:
                while self.running:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                self.stop()
                
        except Exception as e:
            logger.error(f"Error starting MCP server: {e}")
            self.stop()
    
    def accept_connections(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                logger.info(f"New connection from {addr}")
                
                # Start a new thread to handle the client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
    
    def handle_client(self, client_socket: socket.socket, addr):
        """Handle communication with a connected client"""
        client_id = f"{addr[0]}:{addr[1]}"
        self.clients[client_id] = client_socket
        
        try:
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break
                    
                # Process the received data
                message = json.loads(data.decode('utf-8'))
                self.process_message(client_id, message)
                
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        
        finally:
            # Clean up when client disconnects
            if client_id in self.clients:
                del self.clients[client_id]
            try:
                client_socket.close()
            except:
                pass
            logger.info(f"Client {client_id} disconnected")
    
    def process_message(self, client_id: str, message: Dict[str, Any]):
        """Process a message from a client"""
        if 'type' not in message:
            self.send_response(client_id, {'status': 'error', 'message': 'Missing message type'})
            return
            
        msg_type = message['type']
        logger.info(f"Received {msg_type} message from {client_id}")
        
        if msg_type == 'fusion_command':
            # Handle Fusion 360 command
            command = message.get('command')
            params = message.get('params', {})
            
            # TODO: Implement actual Fusion 360 API integration
            result = self.execute_fusion_command(command, params)
            self.send_response(client_id, {
                'status': 'success',
                'type': 'command_result',
                'command': command,
                'result': result
            })
            
        elif msg_type == 'get_model_info':
            # Return information about the current model
            model_info = self.get_model_info()
            self.send_response(client_id, {
                'status': 'success',
                'type': 'model_info',
                'data': model_info
            })

        elif msg_type == 'llm_request':
            prompt = message.get('prompt', '')
            model = message.get('model', 'gpt-3.5-turbo')
            result = self.handle_llm_request(prompt, model)
            self.send_response(client_id, {
                'status': 'success' if 'error' not in result else 'error',
                'type': 'llm_result',
                'data': result
            })

        else:
            self.send_response(client_id, {
                'status': 'error',
                'message': f'Unknown message type: {msg_type}'
            })
    
    def send_response(self, client_id: str, response: Dict[str, Any]):
        """Send a response to a client"""
        if client_id not in self.clients:
            logger.warning(f"Attempted to send response to unknown client {client_id}")
            return
            
        try:
            data = json.dumps(response).encode('utf-8')
            self.clients[client_id].sendall(data)
        except Exception as e:
            logger.error(f"Error sending response to {client_id}: {e}")
            
    def execute_fusion_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command in Fusion 360"""
        # This is a placeholder. In a real implementation, this would
        # interact with the Fusion 360 API to execute commands
        logger.info(f"Executing Fusion command: {command} with params: {params}")
        
        # Mock response for demonstration
        return {
            'command': command,
            'executed': True,
            'message': f"Command {command} executed successfully"
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model in Fusion 360"""
        # This is a placeholder. In a real implementation, this would
        # retrieve actual model data from Fusion 360
        return {
            'name': 'Example Model',
            'version': '1.0',
            'components': [
                {'id': 'comp1', 'name': 'Component 1'},
                {'id': 'comp2', 'name': 'Component 2'}
            ]
        }

    def handle_llm_request(self, prompt: str, model: str) -> Dict[str, Any]:
        """Send a prompt to an LLM and return the response"""
        if openai is None:
            return {'error': 'openai package not installed'}

        if not self.openai_api_key:
            return {'error': 'OPENAI_API_KEY not configured'}

        try:
            openai.api_key = self.openai_api_key
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{'role': 'user', 'content': prompt}]
            )
            content = response['choices'][0]['message']['content']
            return {'response': content}
        except Exception as exc:
            logger.error(f"LLM request failed: {exc}")
            return {'error': str(exc)}
    
    def stop(self):
        """Stop the MCP server"""
        self.running = False
        
        # Close all client connections
        for client_id, client_socket in self.clients.items():
            try:
                client_socket.close()
            except:
                pass
        self.clients.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            
        logger.info("MCP Server stopped")


if __name__ == "__main__":
    # Create and start the MCP server
    server = MCPServer()
    server.start() 