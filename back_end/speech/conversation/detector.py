"""Conversation end detection."""

from datetime import datetime, timedelta
from typing import Optional, Callable

from .state import ConversationState


class EndDetector:
    """Detects when entire conversation has ended."""
    
    def __init__(
        self,
        silence_threshold_seconds: float = 10.0,
        on_conversation_end: Optional[Callable[[ConversationState], None]] = None
    ):
        """Initialize end detector.
        
        Args:
            silence_threshold_seconds: Seconds of silence before considering conversation ended
            on_conversation_end: Callback called with conversation_state when conversation ends
        """
        self.silence_threshold = timedelta(seconds=silence_threshold_seconds)
        self.on_conversation_end = on_conversation_end
    
    def check(self, conversation_state: ConversationState, current_time: datetime) -> bool:
        """Check if conversation should end.
        
        Args:
            conversation_state: Current conversation state
            current_time: Current timestamp
            
        Returns:
            True if conversation should end, False otherwise
        """
        # Check silence threshold
        if conversation_state.last_speech_time:
            silence_duration = current_time - conversation_state.last_speech_time
            if silence_duration >= self.silence_threshold:
                # Phase 2: Can also check person_present flag here
                if conversation_state.person_present is False:
                    # Person walked away
                    if self.on_conversation_end:
                        self.on_conversation_end(conversation_state)
                    return True
                elif conversation_state.person_present is None:
                    # Phase 1: Only silence-based detection
                    if self.on_conversation_end:
                        self.on_conversation_end(conversation_state)
                    return True
        
        return False

