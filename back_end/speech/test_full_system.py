#!/usr/bin/env python3
"""End-to-end test for the full agentic conversation framework.

Tests the complete pipeline: microphone → speech handler → orchestrator → agent → response.
"""

import sys
import os
import time
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from speech.conversation.orchestrator import ConversationOrchestrator

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False


def test_with_microphone(orchestrator: ConversationOrchestrator):
    """Test full system with microphone input."""
    if not PYAUDIO_AVAILABLE:
        print("pyaudio not available. Cannot test with microphone.")
        return False
    
    print("=" * 70)
    print("Full System Test - Microphone Input")
    print("=" * 70)
    print()
    print("The system will:")
    print("  1. Listen to your microphone")
    print("  2. Transcribe your speech")
    print("  3. Detect when you finish speaking (turn detection)")
    print("  4. Send your utterance to the agent")
    print("  5. Get agent response")
    print("  6. Continue the conversation")
    print()
    print("Speak naturally. The system will detect when you pause.")
    print("Press Ctrl+C to stop.")
    print()
    print("=" * 70)
    print()
    
    # Set up audio input
    CHUNK = 1600  # 0.1 seconds at 16kHz
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    audio = pyaudio.PyAudio()
    
    try:
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        print("Recording...")
        orchestrator.start()
        
        try:
            while True:
                # Read audio chunk
                audio_data = stream.read(CHUNK, exception_on_overflow=False)
                
                # Process through orchestrator
                orchestrator.process_audio_chunk(audio_data)
                
                # Small sleep to avoid busy waiting
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n\nStopping...")
        finally:
            stream.stop_stream()
            stream.close()
    
    finally:
        audio.terminate()
        orchestrator.stop()
        print("✓ Stopped")
    
    return True


def test_with_simulated_audio(orchestrator: ConversationOrchestrator):
    """Test full system with simulated audio (for CI/testing)."""
    print("=" * 70)
    print("Full System Test - Simulated Audio")
    print("=" * 70)
    print()
    print("Note: This sends silent audio chunks.")
    print("For real testing, use microphone input (requires pyaudio).")
    print()
    
    orchestrator.start()
    
    chunk_size = 1600  # 0.1 seconds
    silent_audio = b'\x00' * chunk_size
    
    print("Sending simulated audio chunks...")
    print("Press Ctrl+C to stop.")
    print()
    
    try:
        for i in range(200):  # 20 seconds
            orchestrator.process_audio_chunk(silent_audio)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        orchestrator.stop()
        print("✓ Stopped")
    
    return True


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test full agentic conversation system")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Use simulated audio instead of microphone"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Run without database (skip if DATABASE_URL not set)"
    )
    args = parser.parse_args()
    
    print("Initializing conversation orchestrator...")
    
    try:
        # Initialize orchestrator
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
        
        print("✓ Orchestrator initialized")
        print()
        
        # Run test
        if args.simulate or not PYAUDIO_AVAILABLE:
            if not args.simulate and not PYAUDIO_AVAILABLE:
                print("pyaudio not available. Using simulated audio.")
                print("(Install pyaudio for microphone testing: pip install pyaudio)")
                print()
            test_with_simulated_audio(orchestrator)
        else:
            test_with_microphone(orchestrator)
        
        return 0
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

