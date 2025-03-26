import adsk.core
import adsk.fusion
import adsk.cam
import traceback
import json
import threading
import time
import os
import sys

# Add client module directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Import our MCP client
from client import MCPClient

# Global variables used to maintain the references to various event handlers
handlers = []
app = None
ui = None
client = None
stop_flag = False

# Event handler for the commandExecuted event
class CommandExecutedHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            # Get the command that was executed
            eventArgs = adsk.core.CommandEventArgs.cast(args)
            command = eventArgs.command
            
            if client and client.connected:
                # Send the command info to the MCP server
                client.execute_fusion_command('command_executed', {
                    'command_id': command.id,
                    'command_name': command.commandDefinition.name
                })
                
        except:
            if ui:
                ui.messageBox('Command executed event failed:\n{}'.format(traceback.format_exc()))

# Event handler for the documentOpened event
class DocumentOpenedHandler(adsk.core.DocumentEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            # Get the document that was opened
            eventArgs = adsk.core.DocumentEventArgs.cast(args)
            doc = eventArgs.document
            
            if client and client.connected:
                # Send document info to the MCP server
                client.execute_fusion_command('document_opened', {
                    'document_name': doc.name,
                    'document_path': doc.path
                })
                
        except:
            if ui:
                ui.messageBox('Document opened event failed:\n{}'.format(traceback.format_exc()))

# Command handler for the MCP connection command
class MCPConnectionCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            global client
            
            # Get the command
            cmd = adsk.core.Command.cast(args.command)
            
            # Get the CommandInputs collection
            inputs = cmd.commandInputs
            
            # Create server settings inputs
            hostInput = inputs.addStringValueInput('hostInput', 'Server Host', '127.0.0.1')
            portInput = inputs.addStringValueInput('portInput', 'Server Port', '8080')
            
            # Connect to server button
            connectBtn = inputs.addBoolValueInput('connectBtn', 'Connect to Server', False)
            
            # Add handlers for the execute and destroy events
            onExecute = MCPConnectionCommandExecuteHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)
            
            onDestroy = MCPConnectionCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            handlers.append(onDestroy)
            
        except:
            if ui:
                ui.messageBox('Command created failed:\n{}'.format(traceback.format_exc()))

# Command executed handler for the MCP connection command
class MCPConnectionCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            global client
            
            # Get the command
            cmd = args.command
            
            # Get the inputs
            inputs = cmd.commandInputs
            hostInput = inputs.itemById('hostInput')
            portInput = inputs.itemById('portInput')
            
            # Get the values
            host = hostInput.value
            port = int(portInput.value)
            
            # Create and connect the client
            client = MCPClient(host, port)
            if client.connect():
                ui.messageBox(f'Successfully connected to MCP server at {host}:{port}')
                
                # Register response handlers
                def command_result_handler(response):
                    result = response.get('result', {})
                    app.log(f"MCP Command result: {result}")
                
                client.register_handler('command_result', command_result_handler)
                
                # Test the connection
                client.get_model_info()
                
            else:
                ui.messageBox(f'Failed to connect to MCP server at {host}:{port}')
                client = None
                
        except:
            if ui:
                ui.messageBox('Command execute failed:\n{}'.format(traceback.format_exc()))

# Command destroy handler for the MCP connection command
class MCPConnectionCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            # Clean up any resources
            pass
        except:
            if ui:
                ui.messageBox('Command destroy failed:\n{}'.format(traceback.format_exc()))

# Worker function for the client communication thread
def client_worker():
    global stop_flag, client
    
    while not stop_flag:
        # Keep the thread alive but don't consume too much CPU
        time.sleep(0.1)
    
    # Disconnect the client when stopping
    if client and client.connected:
        client.disconnect()
        client = None

def run(context):
    global handlers
    global app
    global ui
    global client
    global stop_flag
    
    try:
        # Initialize Fusion 360 API
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        # Create a new command
        mcpWorkspace = ui.workspaces.itemById('FusionSolidEnvironment')
        tbPanels = mcpWorkspace.toolbarPanels
        mcpPanel = tbPanels.add('MCPPanel', 'MCP Controls')
        
        # Add the command
        controls = mcpPanel.controls
        mcpCommandDef = ui.commandDefinitions.addButtonDefinition(
            'MCPConnectionBtn', 
            'Connect to MCP Server', 
            'Connect to the Fusion 360 Master Control Program server', 
            './resources/MCPIcon'
        )
        
        # Add handlers for the command
        onCommandCreated = MCPConnectionCommandCreatedHandler()
        mcpCommandDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)
        
        # Add the button to the panel
        mcpButton = controls.addCommand(mcpCommandDef)
        mcpButton.isPromoted = True
        mcpButton.isPromotedByDefault = True
        
        # Add event handlers for Fusion 360 events
        cmdExecutedHandler = CommandExecutedHandler()
        app.userInterface.commandExecuted.add(cmdExecutedHandler)
        handlers.append(cmdExecutedHandler)
        
        docOpenedHandler = DocumentOpenedHandler()
        app.documentOpened.add(docOpenedHandler)
        handlers.append(docOpenedHandler)
        
        # Start client worker thread
        stop_flag = False
        client_thread = threading.Thread(target=client_worker)
        client_thread.daemon = True
        client_thread.start()
        
        ui.messageBox('MCP Add-in Started')
        
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    global handlers
    global app
    global ui
    global stop_flag
    
    try:
        # Signal the client thread to stop
        stop_flag = True
        
        # Clean up command definitions
        ui.commandDefinitions.itemById('MCPConnectionBtn').deleteMe()
        
        # Clean up the panel
        mcpWorkspace = ui.workspaces.itemById('FusionSolidEnvironment')
        panel = mcpWorkspace.toolbarPanels.itemById('MCPPanel')
        if panel:
            panel.deleteMe()
        
        # Clean up event handlers
        handlers = []
        
        ui.messageBox('MCP Add-in Stopped')
        
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc())) 