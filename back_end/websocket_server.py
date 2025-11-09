"""WebSocket server for receiving audio from Mentra app and sending notifications."""

import asyncio
import json
import os
import sys
import socket
import struct
import threading
from typing import Dict, Optional, Callable
from dotenv import load_dotenv

try:
    import websockets
    from websockets import serve
    from websockets.legacy.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

# Add back_end to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from speech.conversation.orchestrator import ConversationOrchestrator
from speech.conversation.database import DatabaseManager
from facial_recognition_service import FacialRecognitionService

# Import ESP32 connection functions from vision setup
vision_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vision")
sys.path.insert(0, vision_path)
try:
    from setup import get_local_ip, _recv_exact
    from voxel_sdk.device_controller import DeviceController
    from voxel_sdk.ble import BleVoxelTransport
    ESP32_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"[WebSocket] Warning: ESP32 imports not available: {e}")
    ESP32_IMPORTS_AVAILABLE = False
    # Create dummy functions to prevent errors
    def get_local_ip():
        return "127.0.0.1"
    def _recv_exact(conn, length):
        return b""
    class DeviceController:
        pass
    class BleVoxelTransport:
        pass

load_dotenv()


class WebSocketServer:
    """WebSocket server that handles audio streaming from Mentra app and ESP32 facial recognition."""
    
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
        
        # ESP32 connection state
        self.esp32_controller: Optional[DeviceController] = None
        self.esp32_conn: Optional[socket.socket] = None
        self.esp32_stream_thread: Optional[threading.Thread] = None
        self.esp32_stop_flag = threading.Event()
        
        # Facial recognition service
        self.facial_recognition_service: Optional[FacialRecognitionService] = None
        
        # Queue for person switch notifications from background thread
        self.person_switch_queue: Optional[asyncio.Queue] = None
        self.main_event_loop: Optional[asyncio.AbstractEventLoop] = None
        
    def setup_esp32_connection(self) -> bool:
        """Set up ESP32 connection (BLE, WiFi, stream).
        
        Returns:
            True if connection successful, False otherwise
        """
        if not ESP32_IMPORTS_AVAILABLE:
            print("[WebSocket] ❌ ESP32 imports not available, cannot connect to ESP32")
            return False
        
        try:
            print("[WebSocket] ===== Setting up ESP32 connection =====")
            
            # Step 1: Connect via Bluetooth
            ble_name = "voxel"
            target_address = ""
            
            print(f"[WebSocket] Step 1: Connecting via Bluetooth (scanning for '{ble_name}')...")
            transport = BleVoxelTransport(device_name=ble_name)
            print("[WebSocket] BLE transport created, attempting connection...")
            transport.connect(target_address)
            print("[WebSocket] BLE connection established!")
            
            self.esp32_controller = DeviceController(transport)
            
            # Get device name
            try:
                info = self.esp32_controller.execute_device_command("get_device_name")
                if isinstance(info, dict):
                    device_name = info.get("device_name", "voxel")
                    print(f"[WebSocket] Connected to device '{device_name}'.")
            except Exception:
                print("[WebSocket] Connected to device.")
            
            # Step 2: Connect to WiFi
            print("\n[WebSocket] Connecting to WiFi...")
            wifi_response = self.esp32_controller.execute_device_command("connectWifi:Adam's|adamantium")
            
            if isinstance(wifi_response, dict):
                if "error" in wifi_response:
                    print(f"[WebSocket] ❌ WiFi Connection Failed: {wifi_response.get('error')}")
                    return False
                else:
                    print("[WebSocket] ✅ WiFi Connected Successfully")
                    if "ip" in wifi_response:
                        print(f"[WebSocket]    Device IP: {wifi_response['ip']}")
                    if "ssid" in wifi_response:
                        print(f"[WebSocket]    SSID: {wifi_response['ssid']}")
            
            # Step 3: Start streaming
            print("\n[WebSocket] Starting stream on port 9000...")
            local_ip = get_local_ip()
            stream_port = 9000
            
            print(f"[WebSocket] 📡 Stream IP: {local_ip}:{stream_port}")
            
            # Set up listener socket
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("", stream_port))
            listener.listen(1)
            print(f"[WebSocket]    ✓ Listener socket ready on port {stream_port}")
            
            # Start the stream on the device
            stream_response = self.esp32_controller.filesystem.start_rdmp_stream(local_ip, stream_port)
            
            if isinstance(stream_response, dict) and "error" in stream_response:
                listener.close()
                error_msg = stream_response.get('error', 'Unknown error')
                print(f"[WebSocket] ❌ Stream Failed: {error_msg}")
                return False
            
            print("[WebSocket] ✅ Stream started successfully")
            print(f"[WebSocket]    Waiting for device to connect...")
            
            # Wait for device to connect
            listener.settimeout(10.0)
            try:
                self.esp32_conn, addr = listener.accept()
                print(f"[WebSocket]    ✓ Device connected from {addr}")
                listener.close()
            except socket.timeout:
                listener.close()
                self.esp32_controller.filesystem.stop_rdmp_stream()
                print("[WebSocket]    ❌ Timeout waiting for device connection")
                return False
            
            # Initialize facial recognition service
            try:
                database_manager = DatabaseManager()
                self.facial_recognition_service = FacialRecognitionService(database_manager=database_manager)
                print("[WebSocket] Facial recognition service initialized")
            except Exception as e:
                print(f"[WebSocket] Warning: Failed to initialize facial recognition service: {e}")
                self.facial_recognition_service = FacialRecognitionService(database_manager=None)
            
            return True
            
        except Exception as e:
            print(f"[WebSocket] Error setting up ESP32 connection: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_esp32_frames(self):
        """Process frames from ESP32 stream in background thread."""
        if not self.esp32_conn:
            return
        
        print("[WebSocket] Starting ESP32 frame processing loop...")
        self.esp32_conn.settimeout(5.0)
        
        try:
            while not self.esp32_stop_flag.is_set():
                # Read frame header (8 bytes: 4-byte magic + 4-byte length)
                header = _recv_exact(self.esp32_conn, 8)
                if not header:
                    print("[WebSocket] ESP32 stream closed by device")
                    break
                
                if header[:4] != b"VXL0":
                    print("[WebSocket] Invalid frame header, stopping")
                    break
                
                frame_len = struct.unpack(">I", header[4:])[0]
                if frame_len <= 0 or frame_len > 5 * 1024 * 1024:
                    print(f"[WebSocket] Invalid frame length: {frame_len}")
                    break
                
                # Read frame payload
                payload = _recv_exact(self.esp32_conn, frame_len)
                if not payload:
                    print("[WebSocket] Failed to read frame payload")
                    break
                
                # Decode frame
                try:
                    import cv2
                    import numpy as np
                    frame_array = np.frombuffer(payload, dtype=np.uint8)
                    image = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                    if image is None:
                        print("[WebSocket] Failed to decode JPEG frame, skipping...")
                        continue
                    # Re-encode as JPEG for processing
                    _, encoded = cv2.imencode('.jpg', image)
                    frame_data = encoded.tobytes()
                except Exception as e:
                    print(f"[WebSocket] Error decoding frame: {e}, using raw data")
                    frame_data = payload
                
                # Process frame through facial recognition service (for WebSocket notifications)
                if self.facial_recognition_service:
                    try:
                        # process_frame returns (person_id, switch_detected)
                        person_id, switch_detected = self.facial_recognition_service.process_frame(frame_data)
                        
                        # If person switch detected, notify all WebSocket clients
                        if switch_detected:
                            person_name = None
                            recap = None
                            
                            if person_id is not None and self.facial_recognition_service.database_manager:
                                # Switch to a person - get name and recap
                                try:
                                    person_name = self.facial_recognition_service.database_manager.get_person_name(person_id)
                                    if not person_name:
                                        person_name = person_id
                                    
                                    # Get latest summary/recap
                                    recap = self.facial_recognition_service.database_manager.get_latest_summary(person_id)
                                except Exception as e:
                                    print(f"[WebSocket] Error getting person info: {e}")
                            # else: person_id is None, so switch to no person
                            
                            # Send person switch notification to all connected clients
                            self._notify_all_clients_person_switch(person_id, person_name, recap)
                    except Exception as e:
                        print(f"[WebSocket] Error processing frame: {e}")
                
                # Also pass frame to all active orchestrators' face handlers
                # This ensures the orchestrator's face handler processes frames and triggers its callbacks
                for connection_id, conn_info in list(self.connections.items()):
                    orchestrator = conn_info.get("orchestrator")
                    if orchestrator and orchestrator.face_handler:
                        try:
                            orchestrator.face_handler.process_frame(frame_data)
                        except Exception as e:
                            print(f"[WebSocket] Error passing frame to orchestrator {connection_id}: {e}")
                
        except socket.timeout:
            print("[WebSocket] ESP32 connection timeout")
        except Exception as e:
            print(f"[WebSocket] Error in ESP32 frame processing: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("[WebSocket] ESP32 frame processing loop stopped")
    
    def _notify_all_clients_person_switch(self, person_id: Optional[str], person_name: Optional[str], recap: Optional[str]):
        """Notify all connected WebSocket clients about person switch.
        
        This method can be called from a background thread. It uses a queue to pass
        the notification to the main event loop.
        
        Args:
            person_id: Person ID (None for no person)
            person_name: Person name
            recap: Recap text
        """
        if person_id:
            print(f"[WebSocket] 🔄 Person switch notification: {person_name} ({person_id})")
        else:
            print(f"[WebSocket] 🔄 Person switch notification: No person")
        
        # Use queue to pass message to main event loop (thread-safe)
        if self.person_switch_queue and self.main_event_loop:
            try:
                # Put notification in queue (non-blocking, thread-safe)
                self.main_event_loop.call_soon_threadsafe(
                    self.person_switch_queue.put_nowait,
                    (person_id, person_name, recap)
                )
            except Exception as e:
                print(f"[WebSocket] Error queuing person switch notification: {e}")
        else:
            print(f"[WebSocket] Warning: Person switch queue not initialized, notification dropped")
    
    def start_esp32_processing(self):
        """Start ESP32 frame processing in background thread."""
        if self.esp32_conn and self.facial_recognition_service:
            self.esp32_stop_flag.clear()
            self.esp32_stream_thread = threading.Thread(target=self._process_esp32_frames, daemon=True)
            self.esp32_stream_thread.start()
            print("[WebSocket] ESP32 frame processing thread started")
    
    def stop_esp32_processing(self):
        """Stop ESP32 frame processing."""
        self.esp32_stop_flag.set()
        if self.esp32_stream_thread:
            self.esp32_stream_thread.join(timeout=2.0)
        
        if self.esp32_conn:
            try:
                self.esp32_conn.close()
            except Exception:
                pass
        
        if self.esp32_controller:
            try:
                self.esp32_controller.filesystem.stop_rdmp_stream()
                self.esp32_controller.disconnect()
            except Exception:
                pass
        
        print("[WebSocket] ESP32 processing stopped")
        
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
            interaction_id = data.get("interaction_id")
            orchestrator.conversation_state.conversation_id = interaction_id
            print(f"[WebSocket] Interaction ID set to: {interaction_id}")
        elif msg_type == "change_name":
            person_name = data.get("person_name")
            new_name = data.get("new_name")
            
            if not new_name:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Missing new_name parameter"
                }))
                return
            
            try:
                if orchestrator.database_manager:
                    # Prefer using person_id from orchestrator if available (more reliable)
                    person_id = orchestrator.conversation_state.current_person_id
                    if person_id:
                        orchestrator.database_manager.update_person_name(person_id, new_name)
                        await websocket.send(json.dumps({
                            "type": "change_name_response",
                            "success": True,
                            "message": f"Updated name to '{new_name}'"
                        }))
                        print(f"[WebSocket] Updated person name to '{new_name}' for person_id {person_id}")
                    elif person_name:
                        # Fallback to person_name matching if person_id not available
                        orchestrator.database_manager.update_person_name_by_name(person_name, new_name)
                        await websocket.send(json.dumps({
                            "type": "change_name_response",
                            "success": True,
                            "message": f"Updated name from '{person_name}' to '{new_name}'"
                        }))
                        print(f"[WebSocket] Updated person name from '{person_name}' to '{new_name}'")
                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "No person_id or person_name provided"
                        }))
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Database manager not available"
                    }))
            except ValueError as e:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
                print(f"[WebSocket] Error updating person name: {e}")
            except Exception as e:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": f"Failed to update person name: {str(e)}"
                }))
                print(f"[WebSocket] Error updating person name: {e}")
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
            recap: Recap text (latest summary for the person) - displayed as description on lines 2-3
        """
        try:
            payload = {
                "type": "switch_interaction_person",
                "person_id": person_id,
                "person_name": person_name or "Unknown",
                "blurb": f"Last seen: 5 min ago" if not recap else None,  # Fallback if no recap
                "recap": recap  # Description/recap to display on lines 2-3
            }
            await websocket.send(json.dumps(payload))
            print(f"[WebSocket] ✅ Sent person switch: {person_name} ({person_id})")
        except Exception as e:
            print(f"[WebSocket] Error sending person switch: {e}")
    
    async def start(self):
        """Start the WebSocket server."""
        print(f"[WebSocket] Starting server on ws://{self.host}:{self.port}")
        
        # Store main event loop and create queue for person switch notifications
        self.main_event_loop = asyncio.get_event_loop()
        self.person_switch_queue = asyncio.Queue()
        
        # Background task to process person switch notifications from ESP32 thread
        async def process_person_switch_queue():
            while True:
                try:
                    person_id, person_name, recap = await self.person_switch_queue.get()
                    # Send to all connected clients
                    for connection_id, conn_info in list(self.connections.items()):
                        websocket = conn_info.get("websocket")
                        if websocket:
                            try:
                                await self._send_person_switch(websocket, person_id, person_name, recap)
                            except Exception as e:
                                print(f"[WebSocket] Error sending person switch to {connection_id}: {e}")
                    self.person_switch_queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"[WebSocket] Error processing person switch queue: {e}")
        
        # Start background task
        person_switch_task = asyncio.create_task(process_person_switch_queue())
        
        # Set up ESP32 connection before starting server
        print("[WebSocket] Attempting to set up ESP32 connection...")
        try:
            if self.setup_esp32_connection():
                # Start ESP32 frame processing
                print("[WebSocket] ESP32 connection successful, starting frame processing...")
                self.start_esp32_processing()
            else:
                print("[WebSocket] Warning: ESP32 connection failed, continuing without facial recognition")
        except Exception as e:
            print(f"[WebSocket] Exception during ESP32 setup: {e}")
            import traceback
            traceback.print_exc()
            print("[WebSocket] Continuing without ESP32 connection...")
        
        async with serve(self.handle_connection, self.host, self.port):
            try:
                await asyncio.Future()  # Run forever
            finally:
                # Cancel background task on shutdown
                person_switch_task.cancel()
                try:
                    await person_switch_task
                except asyncio.CancelledError:
                    pass
    
    def run(self):
        """Run the WebSocket server (blocking)."""
        # Suppress noisy handshake errors from websockets library
        import logging
        logging.getLogger("websockets.server").setLevel(logging.ERROR)
        
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            print("\n[WebSocket] Shutting down...")
            self.stop_esp32_processing()


if __name__ == "__main__":
    host = os.getenv("WS_HOST", "localhost")
    port = int(os.getenv("WS_PORT", "8765"))
    
    server = WebSocketServer(host=host, port=port)
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n[WebSocket] Shutting down...")
        server.stop_esp32_processing()

