"""Notification tool for displaying notifications."""

from langchain.tools import tool
from typing import Dict, Any


@tool(return_direct=True)
def notification_tool(title: str, message: str, **kwargs: Any) -> str:
    """Display a notification to the user.
    
    This is a placeholder tool for notification display.
    In production, this would send notifications to the AR glasses display.
    
    Args:
        title: Notification title
        message: Notification message content
        **kwargs: Additional parameters (e.g., priority, duration)
        
    Returns:
        Confirmation of notification display
    """
    print(f"[TOOL CALL] notification_tool(title='{title}', message='{message}', kwargs={kwargs})")
    
    # Placeholder implementation
    result = f"Displayed notification: {title} - {message}"
    
    print(f"[TOOL RESULT] {result}")
    return result

