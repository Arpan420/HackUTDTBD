"""Turn boundary detection using VAD and silence thresholds."""

import re
from datetime import datetime, timedelta
from typing import Optional, Callable


class TurnDetector:
    """Detects when user has finished speaking (turn boundary)."""
    
    def __init__(
        self,
        silence_threshold_seconds: float = 1.5,
        on_turn_complete: Optional[Callable[[str, datetime], None]] = None
    ):
        """Initialize turn detector.
        
        Args:
            silence_threshold_seconds: Seconds of silence before considering turn complete
            on_turn_complete: Callback called with (utterance, timestamp) when turn is complete
        """
        self.silence_threshold = timedelta(seconds=silence_threshold_seconds)
        self.on_turn_complete = on_turn_complete
        
        # State tracking
        self.is_speaking = False
        self.last_speech_time: Optional[datetime] = None
        self.current_utterance = ""
        self.last_update_time: Optional[datetime] = None
    
    def process_speech(self, text: str, timestamp: datetime) -> None:
        """Process incoming speech transcription.
        
        Args:
            text: Transcribed text chunk
            timestamp: When the speech was detected
        """
        self.is_speaking = True
        self.last_speech_time = timestamp
        self.last_update_time = timestamp
        
        # Accumulate text
        if self.current_utterance:
            self.current_utterance += " " + text
        else:
            self.current_utterance = text
        
        # Check for punctuation (turn signal)
        if self._has_complete_punctuation(self.current_utterance):
            self._complete_turn(timestamp)
    
    def check_silence(self, current_time: datetime) -> None:
        """Check if silence threshold has been met.
        
        Args:
            current_time: Current timestamp
        """
        if not self.is_speaking or not self.last_speech_time:
            return
        
        silence_duration = current_time - self.last_speech_time
        if silence_duration >= self.silence_threshold:
            if self.current_utterance.strip():
                self._complete_turn(current_time)
            else:
                # Reset if no utterance accumulated
                self._reset()
    
    def _has_complete_punctuation(self, text: str) -> bool:
        """Check if text ends with complete punctuation.
        
        Args:
            text: Text to check
            
        Returns:
            True if text ends with sentence-ending punctuation
        """
        # Remove trailing whitespace
        text = text.strip()
        if not text:
            return False
        
        # Check for sentence-ending punctuation
        return bool(re.search(r'[.!?]\s*$', text))
    
    def _complete_turn(self, timestamp: datetime) -> None:
        """Complete the current turn and emit event.
        
        Args:
            timestamp: When the turn was completed
        """
        if self.current_utterance.strip() and self.on_turn_complete:
            self.on_turn_complete(self.current_utterance.strip(), timestamp)
        
        self._reset()
    
    def _reset(self) -> None:
        """Reset turn detector state."""
        self.is_speaking = False
        self.current_utterance = ""
        self.last_speech_time = None
    
    def force_complete(self, timestamp: Optional[datetime] = None) -> Optional[str]:
        """Force complete current turn if there's accumulated text.
        
        Args:
            timestamp: Optional timestamp (uses current time if not provided)
            
        Returns:
            Completed utterance if any, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        utterance = self.current_utterance.strip()
        if utterance:
            self._complete_turn(timestamp)
            return utterance
        
        self._reset()
        return None

