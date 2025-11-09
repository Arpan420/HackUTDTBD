"""Notification tool for displaying notifications."""

from langchain.tools import tool
from typing import Dict, Any, Optional, Callable


# Global callback for notification tool
_notification_callback: Optional[Callable[[str, str], None]] = None


def set_notification_callback(callback: Optional[Callable[[str, str], None]]) -> None:
    """Set the callback function to be called when notification tool is executed.
    
    Args:
        callback: Function that takes (title: str, message: str) and returns None
    """
    global _notification_callback
    _notification_callback = callback


@tool(return_direct=True)
def notification_tool(title: str, message: str, **kwargs: Any) -> str:
    """Display a notification to the user.
    
    This tool sends notifications to the AR glasses display via WebSocket.
    
    Args:
        title: Notification title
        message: Notification message content
        **kwargs: Additional parameters (e.g., priority, duration)
        
    Returns:
        Confirmation of notification display
    """
    print(f"[TOOL CALL] notification_tool(title='{title}', message='{message}', kwargs={kwargs})")
    
    # Call the callback if it's set
    if _notification_callback:
        try:
            _notification_callback(title, message)
        except Exception as e:
            print(f"[ERROR] Notification callback failed: {e}")
    
    # Placeholder implementation
    result = f"Displayed notification: {title} - {message}"
    
    print(f"[TOOL RESULT] {result}")
    return result

