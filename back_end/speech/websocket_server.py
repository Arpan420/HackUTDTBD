"""WebSocket server for receiving audio from Mentra app and sending notifications."""

import asyncio
import json
import os
from typing import Dict, Optional, Callable
from dotenv import load_dotenv

try:
    import websockets
    from websockets import serve
    from websockets.legacy.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from conversation.orchestrator import ConversationOrchestrator
from conversation.database import DatabaseManager

load_dotenv()


class WebSocketServer:
    """WebSocket server that handles audio streaming from Mentra app."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """Initialize WebSocket server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library is not installed. "
                "Install it with: pip install websockets"
            )
        
        self.host = host
        self.port = port
        self.connections: Dict[str, Dict] = {}  # connection_id -> {ws, orchestrator}
        
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str = ""):
        """Handle a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            path: Connection path (optional, for compatibility with websockets library)
        """
        # Get remote address safely - may not be available during handshake
        try:
            remote_addr = getattr(websocket, 'remote_address', None)
            if remote_addr:
                connection_id = f"{remote_addr[0]}:{remote_addr[1]}"
            else:
                connection_id = "unknown"
        except Exception:
            connection_id = "unknown"
        
        print(f"[WebSocket] New connection: {connection_id} (path: {path})")
        
        # Initialize orchestrator for this connection
        background_tasks = []  # Store tasks for cleanup
        try:
            database_manager = None
            try:
                database_manager = DatabaseManager()
            except Exception as e:
                print(f"[WebSocket] Warning: Database not available: {e}")
            
            orchestrator = ConversationOrchestrator(database_manager=database_manager)
            
            # Set up callbacks
            # Store websocket in closure for callbacks
            ws_ref = websocket
            
            # Create a queue to pass messages from sync context to async context
            notification_queue = asyncio.Queue()
            person_switch_queue = asyncio.Queue()
            
            async def _send_notification_async(title: str, message: str):
                """Async helper to send notification."""
                try:
                    await self._send_notification(ws_ref, title, message)
                except Exception as e:
                    print(f"[WebSocket] Error sending notification: {e}")
            
            async def _send_person_switch_async(person_id: Optional[str], person_name: Optional[str], recap: Optional[str] = None):
                """Async helper to send person switch."""
                try:
                    await self._send_person_switch(ws_ref, person_id, person_name, recap)
                except Exception as e:
                    print(f"[WebSocket] Error sending person switch: {e}")
            
            # Background task to process queued notifications
            async def process_notification_queue():
                while True:
                    try:
                        title, message = await notification_queue.get()
                        await _send_notification_async(title, message)
                        notification_queue.task_done()
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        print(f"[WebSocket] Error processing notification queue: {e}")
            
            # Background task to process queued person switches
            async def process_person_switch_queue():
                while True:
                    try:
                        person_id, person_name, recap = await person_switch_queue.get()
                        await _send_person_switch_async(person_id, person_name, recap)
                        person_switch_queue.task_done()
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        print(f"[WebSocket] Error processing person switch queue: {e}")
            
            # Start background tasks
            notification_task = asyncio.create_task(process_notification_queue())
            person_switch_task = asyncio.create_task(process_person_switch_queue())
            
            # Store tasks for cleanup
            background_tasks.extend([notification_task, person_switch_task])
            
            # Wrap async callbacks to be called from sync context (tool execution)
            def on_notification_sync(title: str, message: str):
                """Callback when notification tool is called (from sync context)."""
                try:
                    # Put notification in queue (non-blocking)
                    notification_queue.put_nowait((title, message))
                except Exception as e:
                    print(f"[WebSocket] Error queuing notification: {e}")
            
            def on_person_switch_sync(person_id: Optional[str], person_name: Optional[str], recap: Optional[str] = None):
                """Callback when person switches (from sync context)."""
                try:
                    # Put person switch in queue (non-blocking)
                    person_switch_queue.put_nowait((person_id, person_name, recap))
                except Exception as e:
                    print(f"[WebSocket] Error queuing person switch: {e}")
            
            # Set orchestrator callbacks (this also sets the notification tool callback)
            orchestrator.set_callbacks(
                on_notification=on_notification_sync,
                on_person_switch=on_person_switch_sync
            )
            
            # Initialize speech handler for audio processing
            try:
                orchestrator.initialize_speech_handler(
                    server="grpc.nvcf.nvidia.com:443",
                    language_code="en-US",
                    sample_rate_hz=16000
                )
                orchestrator.start()
            except Exception as e:
                print(f"[WebSocket] Warning: Failed to initialize speech handler: {e}")
                print("[WebSocket] Continuing without speech handler - audio processing disabled")
            
            # Store connection info
            self.connections[connection_id] = {
                "websocket": websocket,
                "orchestrator": orchestrator
            }
            
            # Send welcome message
            await websocket.send(json.dumps({
                "type": "connected",
                "message": "WebSocket connection established"
            }))
            
            # Handle messages
            try:
                async for message in websocket:
                    if isinstance(message, bytes):
                        # Binary message = audio chunk
                        await self._handle_audio_chunk(orchestrator, message)
                    elif isinstance(message, str):
                        # Text message = control message
                        try:
                            data = json.loads(message)
                            await self._handle_control_message(websocket, orchestrator, data)
                        except json.JSONDecodeError:
                            print(f"[WebSocket] Invalid JSON: {message}")
            
            except websockets.exceptions.ConnectionClosed:
                print(f"[WebSocket] Connection closed normally: {connection_id}")
            except websockets.exceptions.InvalidMessage as e:
                print(f"[WebSocket] Invalid message (connection may have closed during handshake): {e}")
            except Exception as e:
                print(f"[WebSocket] Error handling connection: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Cleanup
                # Cancel background tasks
                try:
                    for task in background_tasks:
                        task.cancel()
                    # Wait for tasks to finish cancelling
                    if background_tasks:
                        await asyncio.gather(*background_tasks, return_exceptions=True)
                except Exception as e:
                    print(f"[WebSocket] Error cancelling background tasks: {e}")
                
                orchestrator.stop()
                if connection_id in self.connections:
                    del self.connections[connection_id]
                print(f"[WebSocket] Connection cleaned up: {connection_id}")
        
        except Exception as e:
            print(f"[WebSocket] Error initializing orchestrator: {e}")
            import traceback
            traceback.print_exc()
            await websocket.close()
    
    async def _handle_audio_chunk(self, orchestrator: ConversationOrchestrator, audio_data: bytes):
        """Handle incoming audio chunk.
        
        Args:
            orchestrator: Conversation orchestrator instance
            audio_data: Raw audio bytes
        """
        try:
            orchestrator.process_audio_chunk(audio_data)
        except Exception as e:
            print(f"[WebSocket] Error processing audio chunk: {e}")
    
    async def _handle_control_message(self, websocket: WebSocketServerProtocol, orchestrator: ConversationOrchestrator, data: dict):
        """Handle control messages from client.
        
        Args:
            websocket: WebSocket connection
            orchestrator: Conversation orchestrator instance
            data: Parsed JSON data
        """
        msg_type = data.get("type")
        
        if msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))
        elif msg_type == "set_interaction_id":
            # Placeholder for ESP32 stream integration
            interaction_id = data.get("interaction_id")
            orchestrator.conversation_state.conversation_id = interaction_id
            print(f"[WebSocket] Interaction ID set to: {interaction_id}")
        else:
            print(f"[WebSocket] Unknown control message type: {msg_type}")
    
    async def _send_notification(self, websocket: WebSocketServerProtocol, title: str, message: str):
        """Send notification message to client.
        
        Args:
            websocket: WebSocket connection
            title: Notification title
            message: Notification message
        """
        try:
            payload = {
                "type": "notification",
                "title": title,
                "message": message
            }
            await websocket.send(json.dumps(payload))
            print(f"[WebSocket] Sent notification: {title} - {message}")
        except Exception as e:
            print(f"[WebSocket] Error sending notification: {e}")
    
    async def _send_person_switch(self, websocket: WebSocketServerProtocol, person_id: Optional[str], person_name: Optional[str], recap: Optional[str] = None):
        """Send person switch message to client.
        
        Args:
            websocket: WebSocket connection
            person_id: Person ID
            person_name: Person name (from database lookup)
            recap: Recap text (latest summary for the person)
        """
        try:
            payload = {
                "type": "switch_interaction_person",
                "person_id": person_id,
                "person_name": person_name or "Unknown",
                "blurb": f"Last seen: 5 min ago" if not recap else None,  # Mocked for now if no recap
                "recap": recap
            }
            await websocket.send(json.dumps(payload))
            print(f"[WebSocket] Sent person switch: {person_name} ({person_id})")
        except Exception as e:
            print(f"[WebSocket] Error sending person switch: {e}")
    
    async def start(self):
        """Start the WebSocket server."""
        print(f"[WebSocket] Starting server on ws://{self.host}:{self.port}")
        async with serve(self.handle_connection, self.host, self.port):
            await asyncio.Future()  # Run forever
    
    def run(self):
        """Run the WebSocket server (blocking)."""
        # Suppress noisy handshake errors from websockets library
        import logging
        logging.getLogger("websockets.server").setLevel(logging.ERROR)
        asyncio.run(self.start())


if __name__ == "__main__":
    host = os.getenv("WS_HOST", "localhost")
    port = int(os.getenv("WS_PORT", "8765"))
    
    server = WebSocketServer(host=host, port=port)
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n[WebSocket] Shutting down...")

