"""Coordinates multiple data streams (speech, face, etc.)."""

from datetime import datetime
from typing import Dict, Any, Optional, Callable
from enum import Enum


class EventType(str, Enum):
    """Types of events that can be emitted."""
    SPEECH = "speech"
    FACE = "face"


class StreamEvent:
    """Unified event structure for all stream types."""
    
    def __init__(self, event_type: EventType, timestamp: datetime, data: Dict[str, Any]):
        """Initialize stream event.
        
        Args:
            event_type: Type of event (SPEECH, FACE, etc.)
            timestamp: When the event occurred
            data: Event-specific data
        """
        self.type = event_type
        self.timestamp = timestamp
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }


class StreamCoordinator:
    """Coordinates multiple data streams and merges events."""
    
    def __init__(self, on_event: Optional[Callable[[StreamEvent], None]] = None):
        """Initialize stream coordinator.
        
        Args:
            on_event: Callback function called when a unified event is ready
        """
        self.on_event = on_event
        self.is_active = False
    
    def emit_speech_event(self, text: str, timestamp: datetime) -> None:
        """Emit a speech transcription event.
        
        Args:
            text: Transcribed text
            timestamp: When the speech was detected
        """
        event = StreamEvent(
            event_type=EventType.SPEECH,
            timestamp=timestamp,
            data={"text": text}
        )
        if self.on_event:
            self.on_event(event)
    
    def emit_face_event(self, person_id: Optional[str], timestamp: datetime, present: bool) -> None:
        """Emit a face recognition event.
        
        Args:
            person_id: Identifier for the detected person (None if not detected)
            timestamp: When the face was detected
            present: Whether a person is present
        """
        event = StreamEvent(
            event_type=EventType.FACE,
            timestamp=timestamp,
            data={"person_id": person_id, "present": present}
        )
        if self.on_event:
            self.on_event(event)
    
    def start(self) -> None:
        """Start the stream coordinator."""
        self.is_active = True
    
    def stop(self) -> None:
        """Stop the stream coordinator."""
        self.is_active = False

