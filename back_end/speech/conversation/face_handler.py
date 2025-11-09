"""Face recognition handler using real facial recognition service."""

import sys
import os
from datetime import datetime
from typing import Optional, Callable

# Add back_end to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from facial_recognition_service import FacialRecognitionService
from .database import DatabaseManager


class FaceHandler:
    """Face recognition handler using FacialRecognitionService.
    
    Processes video frames and detects person switches, calling callbacks
    when persons are detected or lost.
    """
    
    def __init__(
        self,
        on_person_detected: Optional[Callable[[str, datetime], None]] = None,
        on_person_lost: Optional[Callable[[str, datetime], None]] = None,
        database_manager: Optional[DatabaseManager] = None
    ):
        """Initialize face handler.
        
        Args:
            on_person_detected: Callback called when a person is detected (person_id, timestamp)
            on_person_lost: Callback called when a person is no longer detected (person_id, timestamp)
            database_manager: Optional database manager (creates new one if not provided)
        """
        self.on_person_detected = on_person_detected
        self.on_person_lost = on_person_lost
        self.is_active = False
        
        # Initialize facial recognition service
        if database_manager is None:
            try:
                database_manager = DatabaseManager()
            except Exception as e:
                print(f"[FaceHandler] Warning: Database not available: {e}")
                database_manager = None
        
        self.facial_recognition_service = FacialRecognitionService(database_manager=database_manager)
        
        # Track previous person for detecting person lost events
        self._previous_person_id: Optional[str] = None
    
    def start(self) -> None:
        """Start face recognition processing."""
        self.is_active = True
        print("[FaceHandler] Started facial recognition processing")
    
    def process_frame(self, frame_data: bytes) -> Optional[str]:
        """Process a video frame through facial recognition.
        
        Args:
            frame_data: Raw frame bytes (JPEG/PNG)
            
        Returns:
            person_id if detected and switch occurred, None otherwise
        """
        if not self.is_active:
            return None
        
        try:
            # Process frame through facial recognition service
            # Returns (person_id, switch_detected)
            person_id, switch_detected = self.facial_recognition_service.process_frame(frame_data)
            
            if switch_detected:
                timestamp = datetime.now()
                
                # Handle person switch callbacks
                if person_id is not None:
                    # Person detected or switched to different person
                    if self.on_person_detected:
                        self.on_person_detected(person_id, timestamp)
                    
                    # If we had a previous person and switched to a new one, notify about previous person lost
                    if self._previous_person_id is not None and self._previous_person_id != person_id:
                        if self.on_person_lost:
                            self.on_person_lost(self._previous_person_id, timestamp)
                else:
                    # Person lost (switched to no person)
                    if self._previous_person_id is not None and self.on_person_lost:
                        self.on_person_lost(self._previous_person_id, timestamp)
                
                # Update previous person ID
                self._previous_person_id = person_id
                
                return person_id
            
            # No switch detected, return current person if available
            return person_id if person_id else None
            
        except Exception as e:
            print(f"[FaceHandler] Error processing frame: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def stop(self) -> None:
        """Stop face recognition processing."""
        self.is_active = False
        print("[FaceHandler] Stopped facial recognition processing")

