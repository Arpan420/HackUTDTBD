"""Face recognition handler (Phase 2 placeholder)."""

from datetime import datetime
from typing import Optional, Callable

from .mock_person_tracker import MockPersonTracker


class FaceHandler:
    """Face recognition handler - Phase 2 placeholder.
    
    Currently uses MockPersonTracker for testing. In Phase 2, this will be
    replaced with actual face recognition.
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
        
        # Initialize mock person tracker
        self.mock_tracker = MockPersonTracker(
            on_person_changed=self._handle_person_changed,
            interval_seconds=10.0
        )
    
    def _handle_person_changed(self, person_id: Optional[str], timestamp: datetime) -> None:
        """Handle person change from mock tracker.
        
        Args:
            person_id: Person ID (or None for "nobody")
            timestamp: When person changed
        """
        if person_id and self.on_person_detected:
            self.on_person_detected(person_id, timestamp)
        elif not person_id and self.on_person_lost:
            # Handle "nobody" state - could call on_person_lost if we track previous person
            pass  # For now, do nothing when switching to nobody
    
    def start(self) -> None:
        """Start face recognition processing."""
        self.is_active = True
        self.mock_tracker.start()
    
    def process_frame(self, frame_data: bytes) -> Optional[str]:
        """Process a video frame (placeholder - returns None for Phase 1).
        
        Args:
            frame_data: Raw frame bytes (JPEG/PNG)
            
        Returns:
            person_id if detected, None otherwise
        """
        # Phase 2: Will implement actual face recognition here
        # For now, return current person from mock tracker
        return self.mock_tracker.get_current_person()
    
    def stop(self) -> None:
        """Stop face recognition processing."""
        self.is_active = False
        self.mock_tracker.stop()

