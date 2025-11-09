"""Conversation state management."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class Message(BaseModel):
    """A single conversation message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    person_id: Optional[str] = None  # Phase 2: will be populated when face recognition is added


class ConversationState(BaseModel):
    """In-memory state for active conversation session."""
    
    messages: List[Message] = Field(default_factory=list)
    last_speech_time: Optional[datetime] = None
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Phase 2 fields (optional for backward compatibility)
    current_person_id: Optional[str] = None
    person_present: Optional[bool] = None
    
    def add_message(self, role: str, content: str, person_id: Optional[str] = None) -> None:
        """Add a message to the conversation."""
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            person_id=person_id
        )
        self.messages.append(message)
        if role == "user":
            self.last_speech_time = datetime.now()
    
    def add_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any) -> None:
        """Record a tool call."""
        self.tool_calls.append({
            "tool": tool_name,
            "args": args,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

