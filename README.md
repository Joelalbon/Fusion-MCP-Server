# Fusion 360 MCP Server

Master Control Program (MCP) server for Autodesk Fusion 360 that enables remote control and automation of Fusion 360 operations.

## Overview

This project implements a client-server architecture that allows external applications to interact with Fusion 360. The server acts as a bridge between clients and the Fusion 360 API, enabling remote execution of commands and retrieval of model information.

## Components

The project consists of three main components:

1. **MCP Server** (`server.py`): A standalone Python server that listens for connections from clients and communicates with Fusion 360.

2. **MCP Client** (`client.py`): A Python client library that connects to the MCP server and provides methods for sending commands and receiving responses.

3. **Fusion 360 Add-in** (`fusion360_mcp_addon.py`): A Fusion 360 add-in that connects to the MCP server and provides the actual integration with the Fusion 360 API.

## Installation

### Server and Client

1. Clone this repository or copy the files to your desired location.
2. Make sure you have Python 3.6+ installed.
3. No additional Python packages are required as the implementation uses only standard library modules.

### Fusion 360 Add-in

1. In Fusion 360, go to the "Scripts and Add-ins" dialog (press Shift+S or find it in the "Design" workspace under "Utilities").
2. Click the "Add-ins" tab, then click the "+" icon next to "My Add-ins".
3. Navigate to the location of the add-in files and select the folder containing `fusion360_mcp_addon.py`.
4. Click "Run" to start the add-in, or "Run on Startup" to have it automatically load when Fusion 360 starts.

## Usage

### Starting the Server

1. Open a command prompt or terminal.
2. Navigate to the directory containing the server files.
3. Run the server:

```
python server.py
```

By default, the server will listen on `127.0.0.1:8080`. You can modify the host and port in the code if needed.

### Connecting Fusion 360 to the Server

1. Start Fusion 360 and make sure the MCP add-in is running.
2. In Fusion 360, look for the "MCP Controls" panel.
3. Click the "Connect to MCP Server" button.
4. Enter the server host and port, then click OK.
5. If successful, you will see a confirmation message.

### Using the Client

You can use the provided client implementation to connect to the server and interact with Fusion 360:

```python
from client import MCPClient

# Create and connect the client
client = MCPClient('127.0.0.1', 8080)
if client.connect():
    # Get model information
    client.get_model_info()
    
    # Execute a Fusion 360 command
    client.execute_fusion_command('create_circle', {
        'center': [0, 0, 0],
        'radius': 10
    })
    
    # Disconnect when done
    client.disconnect()
```

## Protocol

The server and clients communicate using a simple JSON-based protocol over TCP sockets. Each message is a JSON object with at least a `type` field indicating the message type.

### Message Types

- `fusion_command`: Execute a command in Fusion 360
- `get_model_info`: Request information about the current model
- `command_result`: Response containing the result of a command execution
- `model_info`: Response containing model information

## Extension

You can extend the server and add-in to support additional functionality:

1. Add new message types to the protocol
2. Implement handlers for these message types in the server
3. Add corresponding methods to the client
4. Implement the actual functionality in the Fusion 360 add-in

## License

This project is provided as-is without any warranty. Use at your own risk.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 

## Notes
- Fusion 360 (2601.1.34)MCP Add-in refuses to install with errors indicating more than one file.
    - Create a new add-in (python), edit, copy the fusion360_mcp_addin.py source to the new file, save, open the new file location and copy the client.py and resource folder to that location, restart Fusion 360.