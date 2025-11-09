"""Speech-to-text handler using NVIDIA Parakeet via streaming API.

Uses NVIDIA NIM high-level streaming API with correct function-id UUID.
Streams audio chunks in real-time and receives transcriptions as they're generated.
"""

import os
import time
import threading
import queue
from datetime import datetime
from typing import Optional, Callable, Iterator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import riva.client
    RIVA_AVAILABLE = True
except ImportError:
    RIVA_AVAILABLE = False


class SpeechHandler:
    """Handles real-time speech-to-text using NVIDIA Parakeet via streaming API.
    
    Uses high-level streaming API which works with NVIDIA NIM when using the correct
    function-id UUID. Streams audio chunks and receives transcriptions in real-time.
    """
    
    def __init__(
        self,
        server: str = "grpc.nvcf.nvidia.com:443",
        language_code: str = "en-US",
        sample_rate_hz: int = 16000,
        on_transcription: Optional[Callable[[str, datetime], None]] = None
    ):
        """Initialize speech handler.
        
        Args:
            server: Riva gRPC server endpoint
            language_code: Language code (e.g., "en-US")
            sample_rate_hz: Audio sample rate in Hz
            on_transcription: Callback function called with (text, timestamp) when transcription is available
        """
        if not RIVA_AVAILABLE:
            raise ImportError(
                "nvidia-riva-client is not installed. "
                "Install it with: pip install nvidia-riva-client"
            )
        
        self.server = server
        self.language_code = language_code
        self.sample_rate_hz = sample_rate_hz
        self.on_transcription = on_transcription
        
        # Get API key from environment
        self.api_key = os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY not found in environment variables or .env file")
        
        # Use high-level Riva client API for batch processing
        self.auth: Optional[riva.client.Auth] = None
        self.asr_service: Optional[riva.client.ASRService] = None
        
        # Streaming queue and thread
        self.audio_queue: queue.Queue = queue.Queue()
        self.response_thread: Optional[threading.Thread] = None
        self.is_streaming = False
        self._stop_event = threading.Event()
    
    def connect(self) -> None:
        """Establish connection to Riva server using high-level API."""
        # Create auth with function-id for NVIDIA NIM
        self.auth = riva.client.Auth(
            uri=self.server,
            use_ssl=True,
            metadata_args=[
                ['authorization', f'Bearer {self.api_key}'],
                ['function-id', '1598d209-5e27-4d3c-8079-4751568b1081']  # NVIDIA NIM function ID UUID
            ]
        )
        self.asr_service = riva.client.ASRService(self.auth)
    
    def _audio_chunks_generator(self) -> Iterator[bytes]:
        """Generator that yields audio chunks from queue for streaming API.
        
        The high-level streaming_response_generator expects an iterable of bytes.
        """
        silence_chunk_size = int(self.sample_rate_hz * 0.1 * 2)  # 100ms of silence
        silence_chunk = b'\x00' * silence_chunk_size
        
        while not self._stop_event.is_set():
            try:
                # Try to get audio with short timeout
                try:
                    audio_data = self.audio_queue.get(block=True, timeout=0.1)
                    
                    if audio_data is None:  # Sentinel value to stop
                        break
                    
                    # Yield real audio chunk (just bytes)
                    yield audio_data
                    
                except queue.Empty:
                    # Queue is empty - yield silence to keep stream alive
                    yield silence_chunk
                    
            except Exception as e:
                print(f"Error in audio chunks generator: {e}")
                import traceback
                traceback.print_exc()
                break
    
    def _process_responses(self) -> None:
        """Process streaming responses in a separate thread.
        
        Only sends final transcriptions to the callback to avoid duplicates.
        """
        try:
            for response in self.stream:
                if self._stop_event.is_set():
                    break
                
                # Process each result in the response
                for result in response.results:
                    if result.alternatives:
                        transcript = result.alternatives[0].transcript
                        is_final = result.is_final
                        
                        if transcript.strip() and is_final:
                            # Final transcription - send to callback
                            timestamp = datetime.now()
                            if self.on_transcription:
                                self.on_transcription(transcript, timestamp)
        except Exception as e:
            print(f"Error processing streaming responses: {e}")
            import traceback
            traceback.print_exc()
    
    def start_streaming(self) -> None:
        """Start streaming recognition using high-level streaming API."""
        if not self.asr_service:
            self.connect()
        
        if self.is_streaming:
            return  # Already streaming
        
        # Reset stop event and clear queue
        self._stop_event.clear()
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        # Create streaming config
        config = riva.client.RecognitionConfig(
            encoding=riva.client.AudioEncoding.LINEAR_PCM,
            sample_rate_hertz=self.sample_rate_hz,
            language_code=self.language_code,
            max_alternatives=1,
            enable_automatic_punctuation=True,
        )
        streaming_config = riva.client.StreamingRecognitionConfig(
            config=config, interim_results=True
        )
        
        # Create streaming response generator (high-level API)
        self.stream = self.asr_service.streaming_response_generator(
            self._audio_chunks_generator(),
            streaming_config
        )
        
        # Start response processing thread
        self.response_thread = threading.Thread(target=self._process_responses, daemon=True)
        self.response_thread.start()
        
        self.is_streaming = True
    
    def process_audio_chunk(self, audio_data: bytes) -> None:
        """Process a chunk of audio data in real-time streaming mode.
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM, mono)
        """
        if not self.is_streaming:
            self.start_streaming()
        
        try:
            # Add audio chunk to queue for streaming processing
            self.audio_queue.put(audio_data, timeout=1.0)
        except queue.Full:
            print("Warning: Audio queue full, dropping chunk")
        except Exception as e:
            print(f"Error processing audio chunk: {e}")
    
    def stop_streaming(self) -> None:
        """Stop streaming recognition."""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        self._stop_event.set()
        
        # Send sentinel to stop generator
        try:
            self.audio_queue.put(None, timeout=0.1)
        except queue.Full:
            pass
        
        # Wait for response thread to finish
        if self.response_thread and self.response_thread.is_alive():
            self.response_thread.join(timeout=2.0)
        
        # Clear queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def disconnect(self) -> None:
        """Close connection."""
        self.stop_streaming()
        self.auth = None
        self.asr_service = None

