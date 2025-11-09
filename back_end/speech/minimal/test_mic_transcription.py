#!/usr/bin/env python3
"""Minimal script to test microphone transcription with NVIDIA NIM Parakeet.

Records audio from microphone, buffers it, and sends to NIM API for transcription.
"""

import os
import sys
import time
import struct
from dotenv import load_dotenv

load_dotenv()

try:
    import riva.client
    import pyaudio
except ImportError as e:
    print(f"Error: {e}")
    print("Install required packages:")
    print("  pip install nvidia-riva-client pyaudio")
    sys.exit(1)


def main():
    """Main function to record and transcribe audio."""
    # Get API key
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("ERROR: NVIDIA_API_KEY not found in .env file")
        return 1
    
    server = "grpc.nvcf.nvidia.com:443"
    sample_rate = 16000
    chunk_duration = 1.6  # seconds - buffer this much audio before sending
    chunk_size = int(sample_rate * chunk_duration * 2)  # 16-bit = 2 bytes/sample
    
    print("=" * 70)
    print("Minimal Microphone Transcription Test")
    print("=" * 70)
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Chunk duration: {chunk_duration} seconds")
    print(f"Buffer size: {chunk_size} bytes")
    print()
    
    # Setup Riva client
    print("Connecting to NVIDIA NIM...")
    try:
        auth = riva.client.Auth(
            uri=server,
            use_ssl=True,
            metadata_args=[
                ['authorization', f'Bearer {api_key}'],
                ['function-id', '1598d209-5e27-4d3c-8079-4751568b1081']  # Correct UUID from NIM docs
            ]
        )
        asr_service = riva.client.ASRService(auth)
        print("✓ Connected")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return 1
    
    # Setup recognition config
    config = riva.client.RecognitionConfig(
        encoding=riva.client.AudioEncoding.LINEAR_PCM,
        sample_rate_hertz=sample_rate,
        language_code='en-US',
        max_alternatives=1,
        enable_automatic_punctuation=True,
    )
    
    # Setup microphone
    print("\nInitializing microphone...")
    audio = pyaudio.PyAudio()
    
    # Find default input device
    try:
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=1600,  # 0.1 seconds
        )
        print("✓ Microphone ready")
    except Exception as e:
        print(f"✗ Microphone error: {e}")
        audio.terminate()
        return 1
    
    print("\n" + "=" * 70)
    print("Recording... Speak into your microphone.")
    print("Press Ctrl+C to stop.")
    print("=" * 70)
    print()
    
    try:
        audio_buffer = []
        buffer_size = 0
        
        while True:
            # Read audio chunk from microphone
            data = stream.read(1600, exception_on_overflow=False)
            audio_buffer.append(data)
            buffer_size += len(data)
            
            # When we have enough audio, send for transcription
            if buffer_size >= chunk_size:
                # Combine all buffered audio
                audio_data = b''.join(audio_buffer)
                audio_buffer.clear()
                buffer_size = 0
                
                # Send to NIM API
                try:
                    response = asr_service.offline_recognize(audio_data, config)
                    
                    # Print transcriptions
                    for result in response.results:
                        if result.alternatives:
                            transcript = result.alternatives[0].transcript
                            if transcript.strip():
                                print(f"[{time.strftime('%H:%M:%S')}] {transcript}")
                
                except Exception as e:
                    print(f"Error: {e}")
                    # Continue recording even if one request fails
                    continue
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
        
        # Process any remaining audio
        if len(audio_buffer) > 0:
            audio_data = b''.join(audio_buffer)
            if len(audio_data) > 0:
                try:
                    response = asr_service.offline_recognize(audio_data, config)
                    for result in response.results:
                        if result.alternatives:
                            transcript = result.alternatives[0].transcript
                            if transcript.strip():
                                print(f"[{time.strftime('%H:%M:%S')}] {transcript}")
                except Exception as e:
                    print(f"Error processing final chunk: {e}")
    
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()
        print("✓ Stopped")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

