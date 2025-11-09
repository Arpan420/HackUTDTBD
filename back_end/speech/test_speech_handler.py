#!/usr/bin/env python3
"""Test script for real-time speech recognition."""

import sys
import os
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from speech.conversation.speech_handler import SpeechHandler

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("Warning: pyaudio not available. Install with: pip install pyaudio")
    print("You can still test with simulated audio data.")


def test_with_microphone():
    """Test speech handler with microphone input."""
    if not PYAUDIO_AVAILABLE:
        print("pyaudio not available. Cannot test with microphone.")
        return False
    
    print("=" * 70)
    print("Real-time Speech Recognition Test")
    print("=" * 70)
    print()
    print("Initializing speech handler...")
    
    transcriptions = []
    
    def on_transcription(text: str, timestamp: datetime):
        """Callback for transcriptions."""
        transcriptions.append((text, timestamp))
        print(f"[{timestamp.strftime('%H:%M:%S')}] {text}")
    
    # Initialize speech handler
    try:
        handler = SpeechHandler(
            server="grpc.nvcf.nvidia.com:443",
            language_code="en-US",
            sample_rate_hz=16000,
            on_transcription=on_transcription
        )
        print("✓ Speech handler initialized")
    except Exception as e:
        print(f"✗ Failed to initialize speech handler: {e}")
        return False
    
    # Connect and start streaming
    try:
        handler.connect()
        print("✓ Connected to Riva server")
        handler.start_streaming()
        print("✓ Streaming started")
    except Exception as e:
        print(f"✗ Failed to start streaming: {e}")
        return False
    
    # Set up audio input
    CHUNK = 1600  # 0.1 seconds at 16kHz (16-bit = 2 bytes per sample)
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    audio = pyaudio.PyAudio()
    
    try:
        print()
        print("Recording... Speak into your microphone.")
        print("Press Ctrl+C to stop.")
        print()
        
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        try:
            while True:
                # Read audio chunk
                audio_data = stream.read(CHUNK, exception_on_overflow=False)
                
                # Process through speech handler
                handler.process_audio_chunk(audio_data)
                
                # Small sleep to avoid busy waiting
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n\nStopping...")
        finally:
            stream.stop_stream()
            stream.close()
    
    finally:
        audio.terminate()
        handler.stop_streaming()
        handler.disconnect()
        print("✓ Disconnected")
    
    # Print summary
    print()
    print("=" * 70)
    print(f"Summary: Received {len(transcriptions)} transcriptions")
    print("=" * 70)
    for text, ts in transcriptions:
        print(f"[{ts.strftime('%H:%M:%S')}] {text}")
    
    return True


def test_with_simulated_audio():
    """Test speech handler with simulated audio data."""
    print("=" * 70)
    print("Simulated Audio Test")
    print("=" * 70)
    print()
    print("Note: This will send empty/silent audio chunks.")
    print("For real testing, use microphone input (requires pyaudio).")
    print()
    
    transcriptions = []
    
    def on_transcription(text: str, timestamp: datetime):
        """Callback for transcriptions."""
        transcriptions.append((text, timestamp))
        print(f"[{timestamp.strftime('%H:%M:%S')}] {text}")
    
    # Initialize speech handler
    try:
        handler = SpeechHandler(
            server="grpc.nvcf.nvidia.com:443",
            language_code="en-US",
            sample_rate_hz=16000,
            on_transcription=on_transcription
        )
        print("✓ Speech handler initialized")
    except Exception as e:
        print(f"✗ Failed to initialize speech handler: {e}")
        return False
    
    # Connect and start streaming
    try:
        handler.connect()
        print("✓ Connected to Riva server")
        handler.start_streaming()
        print("✓ Streaming started")
    except Exception as e:
        print(f"✗ Failed to start streaming: {e}")
        return False
    
    # Simulate audio chunks (silent audio)
    print()
    print("Sending simulated audio chunks (silent)...")
    print("Press Ctrl+C to stop.")
    print()
    
    chunk_size = 1600  # 0.1 seconds at 16kHz
    silent_audio = b'\x00' * chunk_size
    
    try:
        for i in range(100):  # Send 10 seconds of silent audio
            handler.process_audio_chunk(silent_audio)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        handler.stop_streaming()
        handler.disconnect()
        print("✓ Disconnected")
    
    print()
    print("=" * 70)
    print(f"Summary: Received {len(transcriptions)} transcriptions")
    print("=" * 70)
    
    return True


def main():
    """Main test function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--simulate":
        # Test with simulated audio
        test_with_simulated_audio()
    else:
        # Try microphone first, fall back to simulation
        if PYAUDIO_AVAILABLE:
            print("Testing with microphone input...")
            print("(Use --simulate flag to test with simulated audio instead)")
            print()
            if not test_with_microphone():
                print("\nFalling back to simulated audio test...")
                test_with_simulated_audio()
        else:
            print("pyaudio not available. Testing with simulated audio...")
            print("(Install pyaudio for microphone testing: pip install pyaudio)")
            print()
            test_with_simulated_audio()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

