#!/usr/bin/env python3
"""Example script demonstrating conversation agent usage with AR glasses."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voxel_sdk.device_controller import DeviceController
from voxel_sdk.ble import BleVoxelTransport
from speech.conversation.orchestrator import ConversationOrchestrator


def main():
    """Main example function."""
    print("=== AR Glasses Conversation Agent Example ===\n")
    
    # Step 1: Connect to AR glasses device
    print("Step 1: Connecting to AR glasses device...")
    ble_name = "voxel"
    transport = BleVoxelTransport(device_name=ble_name)
    
    try:
        transport.connect("")
        controller = DeviceController(transport)
        print("✓ Connected to device\n")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return 1
    
    # Step 2: Initialize conversation orchestrator
    print("Step 2: Initializing conversation agent...")
    orchestrator = ConversationOrchestrator(
        silence_threshold_seconds=1.5,
        end_silence_threshold_seconds=10.0
    )
    
    # Initialize speech handler
    orchestrator.initialize_speech_handler(
        server="grpc.nvcf.nvidia.com:443",
        language_code="en-US",
        sample_rate_hz=16000
    )
    print("✓ Conversation agent initialized\n")
    
    # Step 3: Start orchestrator
    print("Step 3: Starting conversation agent...")
    print("Note: This example assumes audio stream is available from device.")
    print("In a real implementation, you would connect to the device's audio stream.\n")
    print("Press Ctrl+C to stop...\n")
    
    try:
        # In a real implementation, you would:
        # 1. Get audio stream from device
        # 2. Process audio chunks with orchestrator.process_audio_chunk()
        # 3. Run orchestrator.run() in a separate thread
        
        # For this example, we'll just demonstrate the structure
        # You would replace this with actual audio streaming logic
        print("Example: Processing audio chunks...")
        print("(In production, this would process real audio from device)\n")
        
        # Example: Simulate processing (remove in production)
        orchestrator.start()
        
        # Run orchestrator (this blocks until stopped)
        orchestrator.run()
        
    except KeyboardInterrupt:
        print("\n\nStopping...")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        orchestrator.stop()
        try:
            controller.disconnect()
        except Exception:
            pass
        print("Disconnected.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

