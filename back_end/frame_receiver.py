"""Frame receiver module for processing frames from ESP32."""

import sys
import os
from typing import Optional

# Add back_end to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from facial_recognition_service import FacialRecognitionService
from speech.conversation.database import DatabaseManager


# Global service instance (initialized on first use)
_facial_recognition_service: Optional[FacialRecognitionService] = None


def _get_service() -> FacialRecognitionService:
    """Get or create facial recognition service instance."""
    global _facial_recognition_service
    
    if _facial_recognition_service is None:
        try:
            database_manager = DatabaseManager()
            _facial_recognition_service = FacialRecognitionService(database_manager=database_manager)
            print("[FrameReceiver] Facial recognition service initialized")
        except Exception as e:
            print(f"[FrameReceiver] Warning: Failed to initialize database: {e}")
            _facial_recognition_service = FacialRecognitionService(database_manager=None)
    
    return _facial_recognition_service


def process_frame(frame_data: bytes) -> tuple[Optional[str], bool]:
    """Process a frame through facial recognition.
    
    Args:
        frame_data: Binary image data (JPEG/PNG) from ESP32
        
    Returns:
        Tuple of (person_id, switch_detected)
        - person_id: Current person ID (None for no person) if switch detected
        - switch_detected: True if person switch was detected, False otherwise
    """
    service = _get_service()
    return service.process_frame(frame_data)

