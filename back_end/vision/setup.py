#!/usr/bin/env python3
"""Script to connect to Voxel device, connect WiFi, and start streaming (log IP only)."""

import sys
import socket
import struct
import os
import threading
import select
import termios
import tty
from datetime import datetime
from voxel_sdk.device_controller import DeviceController
from voxel_sdk.ble import BleVoxelTransport

# Import frame receiver for facial recognition
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from frame_receiver import process_frame as process_frame_recognition
    FRAME_RECEIVER_AVAILABLE = True
except ImportError as e:
    print(f"[Vision] Warning: Frame receiver not available: {e}")
    FRAME_RECEIVER_AVAILABLE = False
    process_frame_recognition = None

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


def get_local_ip() -> str:
    """Get the local IP address for streaming (same logic as voxel.py)."""
    def valid(ip: str) -> bool:
        return ip and not ip.startswith("127.") and ip != "0.0.0.0"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as temp:
            temp.connect(("8.8.8.8", 80))
            candidate = temp.getsockname()[0]
            if valid(candidate):
                return candidate
    except Exception:
        pass

    try:
        hostname_ips = socket.gethostbyname_ex(socket.gethostname())[2]
        for ip in hostname_ips:
            if valid(ip):
                return ip
    except Exception:
        pass

    raise RuntimeError("Unable to determine local IP address for streaming")


def _recv_exact(conn: socket.socket, length: int) -> bytes:
    """Receive exactly 'length' bytes from the socket."""
    remaining = length
    chunks = []
    while remaining > 0:
        chunk = conn.recv(remaining)
        if not chunk:
            return b""
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def processFrame(frame_data: bytes, timestamp: str) -> None:
    """Process a frame: save to tmp/ in workspace directory with timestamp and process through facial recognition."""
    # Process frame through facial recognition
    if FRAME_RECEIVER_AVAILABLE and process_frame_recognition:
        try:
            person_id, switch_detected = process_frame_recognition(frame_data)
            if switch_detected:
                if person_id:
                    print(f"[Vision] Person switch detected: {person_id}")
                else:
                    print(f"[Vision] Person switch detected: No person")
        except Exception as e:
            print(f"[Vision] Error processing frame through recognition: {e}")
    
    # Also save to tmp for debugging (optional)
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(workspace_dir, "tmp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create filename with timestamp
    filename = f"frame_{timestamp}.jpg"
    filepath = os.path.join(temp_dir, filename)
    
    # Save frame
    with open(filepath, "wb") as f:
        f.write(frame_data)
    
    # Print message
    file_size = len(frame_data)
    print(f"📸 Frame saved: {filepath} ({file_size} bytes)")


def main():
    # Step 1: Connect to device via Bluetooth
    ble_name = "voxel"  # Device name prefix to search for
    target_address = ""  # Optional: specific BLE address, or "" to scan
    
    print(f"Connecting via Bluetooth (scanning for '{ble_name}')...")
    
    transport = BleVoxelTransport(device_name=ble_name)
    try:
        transport.connect(target_address)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return 1
    
    controller = DeviceController(transport)
    
    try:
        # Get device name
        try:
            info = controller.execute_device_command("get_device_name")
            if isinstance(info, dict):
                device_name = info.get("device_name", "voxel")
                print(f"Connected to device '{device_name}'.")
        except Exception:
            print("Connected to device.")
        
        # Step 2: Connect to WiFi
        # print("\nConnecting to WiFi: GL-SFT1200-b40...")
        # wifi_response = controller.execute_device_command("connectWifi:GL-SFT1200-b40|goodlife")

        print("\nConnecting to WiFi: ApamDaGoat...")
        wifi_response = controller.execute_device_command("connectWifi:Adam's|adamantium")
        
        if isinstance(wifi_response, dict):
            if "error" in wifi_response:
                print(f"❌ WiFi Connection Failed: {wifi_response.get('error')}")
                return 1
            else:
                print("✅ WiFi Connected Successfully")
                if "ip" in wifi_response:
                    print(f"   Device IP: {wifi_response['ip']}")
                if "ssid" in wifi_response:
                    print(f"   SSID: {wifi_response['ssid']}")
        else:
            print(f"WiFi response: {wifi_response}")
        
        # Step 3: Start streaming and log the IP
        print("\nStarting stream on port 9000...")
        
        # Get the local IP address that the device will connect to
        local_ip = get_local_ip()
        stream_port = 9000
        
        # Get device IP for verification
        device_ip = None
        if isinstance(wifi_response, dict) and "ip" in wifi_response:
            device_ip = wifi_response["ip"]
        
        print(f"📡 Stream IP: {local_ip}:{stream_port}")
        print(f"   Device will stream to: {local_ip}:{stream_port}")
        if device_ip:
            print(f"   Device IP: {device_ip}")
            # Check if they're on the same network
            local_network = ".".join(local_ip.split(".")[:3])
            device_network = ".".join(device_ip.split(".")[:3])
            if local_network == device_network:
                print(f"   ✓ Device and computer are on the same network ({local_network}.x)")
            else:
                print(f"   ⚠ Warning: Device ({device_network}.x) and computer ({local_network}.x) are on different networks!")
        
        # Set up listener socket FIRST (like stream_with_visualization does)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("", stream_port))
        listener.listen(1)
        print(f"   ✓ Listener socket ready on port {stream_port}")
        
        # Now start the stream on the device
        stream_response = controller.filesystem.start_rdmp_stream(local_ip, stream_port)
        
        if isinstance(stream_response, dict) and "error" in stream_response:
            listener.close()
            error_msg = stream_response.get('error', 'Unknown error')
            print(f"❌ Stream Failed: {error_msg}")
            if "Failed to connect" in error_msg:
                print("   💡 Tip: Make sure your computer's firewall allows connections on port 9000")
                print("   💡 Tip: Verify device and computer are on the same WiFi network")
            return 1
        
        print("✅ Stream started successfully")
        print(f"   Waiting for device to connect...")
        
        # Wait for device to connect
        listener.settimeout(10.0)
        try:
            conn, addr = listener.accept()
            print(f"   ✓ Device connected from {addr}")
            listener.close()
        except socket.timeout:
            listener.close()
            controller.filesystem.stop_rdmp_stream()
            print("   ❌ Timeout waiting for device connection")
            return 1
        
        # Check if OpenCV is available for frame decoding
        if cv2 is None or np is None:
            print("⚠️  Warning: OpenCV/numpy not available. Frames will be saved as raw JPEG data.")
        
        # Set up recording toggle with thread-safe flag
        recording_enabled = threading.Event()
        recording_enabled.set()  # Start with recording enabled
        stop_io_thread = threading.Event()
        
        def io_thread_func():
            """Thread function to monitor keypresses for recording toggle."""
            # Set up terminal for non-blocking keypress detection
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())
                while not stop_io_thread.is_set():
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1)
                        if key == 'r' or key == 'R':
                            if recording_enabled.is_set():
                                recording_enabled.clear()
                                print("\n🔄 Recording: OFF")
                            else:
                                recording_enabled.set()
                                print("\n🔄 Recording: ON")
                        elif key == '\x03':  # Ctrl+C
                            stop_io_thread.set()
                            break
            finally:
                # Restore terminal settings
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        
        # Start I/O thread
        io_thread = threading.Thread(target=io_thread_func, daemon=True)
        io_thread.start()
        
        # Process frames from the stream
        print("\nProcessing frames. Press 'r' to toggle recording, Ctrl+C to stop...")
        print("Recording: ON")
        conn.settimeout(5.0)
        try:
            while True:
                if stop_io_thread.is_set():
                    break
                    
                # Read frame header (8 bytes: 4-byte magic + 4-byte length)
                header = _recv_exact(conn, 8)
                if not header:
                    print("Stream closed by device")
                    break
                
                if header[:4] != b"VXL0":
                    print("Invalid frame header, stopping")
                    break
                
                frame_len = struct.unpack(">I", header[4:])[0]
                if frame_len <= 0 or frame_len > 5 * 1024 * 1024:
                    print(f"Invalid frame length: {frame_len}")
                    break
                
                # Read frame payload
                payload = _recv_exact(conn, frame_len)
                if not payload:
                    print("Failed to read frame payload")
                    break
                
                # Decode frame if OpenCV is available, otherwise use raw data
                if cv2 is not None and np is not None:
                    try:
                        frame_array = np.frombuffer(payload, dtype=np.uint8)
                        image = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                        if image is None:
                            print("Failed to decode JPEG frame, skipping...")
                            continue
                        # Re-encode as JPEG for saving
                        _, encoded = cv2.imencode('.jpg', image)
                        frame_data = encoded.tobytes()
                    except Exception as e:
                        print(f"Error decoding frame: {e}, using raw data")
                        frame_data = payload
                else:
                    frame_data = payload
                
                # Process frame with timestamp (only if recording is enabled)
                if recording_enabled.is_set():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
                    processFrame(frame_data, timestamp)
                
        except socket.timeout:
            print("Connection timeout")
        except KeyboardInterrupt:
            print("\nStopping stream...")
        finally:
            stop_io_thread.set()
            conn.close()
            controller.filesystem.stop_rdmp_stream()
            print("Stream stopped.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        try:
            controller.disconnect()
        except Exception:  # noqa: BLE001
            pass
        print("Disconnected.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())