"""Face recognition handler (Phase 2 placeholder)."""

from datetime import datetime
from typing import Optional, Callable


class FaceHandler:
    """Face recognition handler - Phase 2 placeholder.
    
    This is a placeholder implementation that will be replaced with actual
    face recognition in Phase 2. Currently returns no-op/empty events.
    """
    
    def __init__(
        self,
        on_person_detected: Optional[Callable[[str, datetime], None]] = None,
        on_person_lost: Optional[Callable[[str, datetime], None]] = None
    ):
        """Initialize face handler.
        
        Args:
            on_person_detected: Callback called when a person is detected (person_id, timestamp)
            on_person_lost: Callback called when a person is no longer detected (person_id, timestamp)
        """
        self.on_person_detected = on_person_detected
        self.on_person_lost = on_person_lost
        self.is_active = False
    
    def start(self) -> None:
        """Start face recognition processing."""
        self.is_active = True
    
    def process_frame(self, frame_data: bytes) -> Optional[str]:
        """Process a video frame (placeholder - returns None for Phase 1).
        
        Args:
            frame_data: Raw frame bytes (JPEG/PNG)
            
        Returns:
            person_id if detected, None otherwise
        """
        # Phase 2: Will implement actual face recognition here
        return None
    
    def stop(self) -> None:
        """Stop face recognition processing."""
        self.is_active = False

