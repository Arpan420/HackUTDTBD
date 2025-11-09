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
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY not set, cannot connect")
        
        try:
            # Create auth with function-id for NVIDIA NIM
            self.auth = riva.client.Auth(
                uri=self.server,
                use_ssl=True,
                metadata_args=[
                    ['authorization', f'Bearer {self.api_key}'],
                    ['function-id', '1598d209-5e27-4d3c-8079-4751568b1081']  # NVIDIA NIM function ID UUID
                ]
            )
        except Exception as e:
            print(f"[SpeechHandler] Error creating auth: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        try:
            self.asr_service = riva.client.ASRService(self.auth)
        except Exception as e:
            print(f"[SpeechHandler] Error creating ASR service: {e}")
            import traceback
            traceback.print_exc()
            self.auth = None
            raise
    
    def _audio_chunks_generator(self) -> Iterator[bytes]:
        """Generator that yields audio chunks from queue for streaming API.
        
        The high-level streaming_response_generator expects an iterable of bytes.
        """
        try:
            silence_chunk_size = int(self.sample_rate_hz * 0.1 * 2)  # 100ms of silence
            silence_chunk = b'\x00' * silence_chunk_size
        except (ValueError, TypeError) as e:
            print(f"[SpeechHandler] Error calculating silence chunk size: {e}")
            silence_chunk = b'\x00' * 3200  # Default fallback
        
        while not self._stop_event.is_set():
            try:
                # Try to get audio with short timeout
                try:
                    audio_data = self.audio_queue.get(block=True, timeout=0.1)
                    
                    if audio_data is None:  # Sentinel value to stop
                        break
                    
                    if not isinstance(audio_data, bytes):
                        print(f"[SpeechHandler] Warning: Non-bytes audio data received: {type(audio_data)}")
                        continue
                    
                    if len(audio_data) == 0:
                        print("[SpeechHandler] Warning: Empty audio chunk received")
                        continue
                    
                    # Yield real audio chunk (just bytes)
                    yield audio_data
                    
                except queue.Empty:
                    # Queue is empty - yield silence to keep stream alive
                    yield silence_chunk
                except queue.Full:
                    print("[SpeechHandler] Warning: Audio queue full in generator")
                    yield silence_chunk
                    
            except KeyboardInterrupt:
                print("[SpeechHandler] Generator interrupted")
                break
            except Exception as e:
                print(f"[SpeechHandler] Error in audio chunks generator: {e}")
                import traceback
                traceback.print_exc()
                break
    
    def _process_responses(self) -> None:
        """Process streaming responses in a separate thread.
        
        Only sends final transcriptions to the callback to avoid duplicates.
        """
        if not hasattr(self, 'stream') or self.stream is None:
            print("[SpeechHandler] Error: Stream not initialized")
            return
        
        try:
            for response in self.stream:
                if self._stop_event.is_set():
                    break
                
                if not response:
                    continue
                
                try:
                    # Process each result in the response
                    if not hasattr(response, 'results') or not response.results:
                        continue
                    
                    for result in response.results:
                        if self._stop_event.is_set():
                            break
                        
                        try:
                            if not hasattr(result, 'alternatives') or not result.alternatives:
                                continue
                            
                            transcript = result.alternatives[0].transcript
                            is_final = result.is_final
                            
                            if transcript and transcript.strip() and is_final:
                                # Final transcription - send to callback
                                try:
                                    timestamp = datetime.now()
                                    if self.on_transcription:
                                        self.on_transcription(transcript, timestamp)
                                except Exception as e:
                                    print(f"[SpeechHandler] Error in transcription callback: {e}")
                                    import traceback
                                    traceback.print_exc()
                        except (AttributeError, IndexError) as e:
                            print(f"[SpeechHandler] Error accessing result data: {e}")
                            continue
                        except Exception as e:
                            print(f"[SpeechHandler] Error processing result: {e}")
                            continue
                except AttributeError as e:
                    print(f"[SpeechHandler] Error accessing response data: {e}")
                    continue
                except Exception as e:
                    print(f"[SpeechHandler] Error processing response: {e}")
                    continue
        except StopIteration:
            print("[SpeechHandler] Stream ended")
        except KeyboardInterrupt:
            print("[SpeechHandler] Response processing interrupted")
        except Exception as e:
            print(f"[SpeechHandler] Error processing streaming responses: {e}")
            import traceback
            traceback.print_exc()
    
    def start_streaming(self) -> None:
        """Start streaming recognition using high-level streaming API."""
        if not self.asr_service:
            try:
                self.connect()
            except Exception as e:
                print(f"[SpeechHandler] Error connecting: {e}")
                raise
        
        if self.is_streaming:
            return  # Already streaming
        
        # Reset stop event and clear queue
        try:
            self._stop_event.clear()
        except Exception as e:
            print(f"[SpeechHandler] Error clearing stop event: {e}")
        
        try:
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
        except Exception as e:
            print(f"[SpeechHandler] Error clearing audio queue: {e}")
        
        # Create streaming config
        try:
            config = riva.client.RecognitionConfig(
                encoding=riva.client.AudioEncoding.LINEAR_PCM,
                sample_rate_hertz=self.sample_rate_hz,
                language_code=self.language_code,
                max_alternatives=1,
                enable_automatic_punctuation=True,
            )
        except Exception as e:
            print(f"[SpeechHandler] Error creating recognition config: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        try:
            streaming_config = riva.client.StreamingRecognitionConfig(
                config=config, interim_results=True
            )
        except Exception as e:
            print(f"[SpeechHandler] Error creating streaming config: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Create streaming response generator (high-level API)
        try:
            self.stream = self.asr_service.streaming_response_generator(
                self._audio_chunks_generator(),
                streaming_config
            )
        except Exception as e:
            print(f"[SpeechHandler] Error creating stream generator: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        # Start response processing thread
        try:
            self.response_thread = threading.Thread(target=self._process_responses, daemon=True)
            self.response_thread.start()
        except Exception as e:
            print(f"[SpeechHandler] Error starting response thread: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        self.is_streaming = True
    
    def process_audio_chunk(self, audio_data: bytes) -> None:
        """Process a chunk of audio data in real-time streaming mode.
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM, mono)
        """
        if not audio_data or len(audio_data) == 0:
            print("[SpeechHandler] Warning: Empty audio chunk received")
            return
        
        if not isinstance(audio_data, bytes):
            print(f"[SpeechHandler] Warning: Non-bytes audio data received: {type(audio_data)}")
            return
        
        if not self.is_streaming:
            try:
                self.start_streaming()
            except Exception as e:
                print(f"[SpeechHandler] Error starting stream: {e}")
                return
        
        try:
            # Add audio chunk to queue for streaming processing
            self.audio_queue.put(audio_data, timeout=1.0)
        except queue.Full:
            print("[SpeechHandler] Warning: Audio queue full, dropping chunk")
        except TypeError as e:
            print(f"[SpeechHandler] Error: Invalid audio data type: {e}")
        except Exception as e:
            print(f"[SpeechHandler] Error processing audio chunk: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_streaming(self) -> None:
        """Stop streaming recognition."""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        
        try:
            self._stop_event.set()
        except Exception as e:
            print(f"[SpeechHandler] Error setting stop event: {e}")
        
        # Send sentinel to stop generator
        try:
            self.audio_queue.put(None, timeout=0.1)
        except queue.Full:
            pass
        except Exception as e:
            print(f"[SpeechHandler] Error sending sentinel: {e}")
        
        # Wait for response thread to finish
        if self.response_thread and self.response_thread.is_alive():
            try:
                self.response_thread.join(timeout=2.0)
            except Exception as e:
                print(f"[SpeechHandler] Error joining response thread: {e}")
        
        # Clear queue
        try:
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
        except Exception as e:
            print(f"[SpeechHandler] Error clearing queue: {e}")
    
    def disconnect(self) -> None:
        """Close connection."""
        try:
            self.stop_streaming()
        except Exception as e:
            print(f"[SpeechHandler] Error stopping stream during disconnect: {e}")
        
        try:
            self.auth = None
            self.asr_service = None
        except Exception as e:
            print(f"[SpeechHandler] Error cleaning up connection: {e}")

