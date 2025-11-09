"""Update name tool for updating person names."""

from langchain.tools import tool
from typing import Dict, Any, Optional, Callable
from ..database import DatabaseManager


# Global database manager reference
_database_manager: Optional[DatabaseManager] = None

# Global function to get current person_id
_current_person_id_getter: Optional[Callable[[], Optional[str]]] = None


def set_database_manager(database_manager: Optional[DatabaseManager]) -> None:
    """Set the database manager to be used by the update_name tool.
    
    Args:
        database_manager: Database manager instance
    """
    global _database_manager
    _database_manager = database_manager


def set_current_person_id_getter(getter: Optional[Callable[[], Optional[str]]]) -> None:
    """Set the function to get the current person_id.
    
    Args:
        getter: Function that returns the current person_id (or None)
    """
    global _current_person_id_getter
    _current_person_id_getter = getter


@tool(return_direct=True)
def update_name_tool(new_name: str, **kwargs: Any) -> str:
    """Update the current person's name in the database.
    
    This tool updates the person_name field in the faces table for the person
    currently in conversation. It ends the conversation turn after execution
    (similar to notification_tool).
    
    Args:
        new_name: New name to set for the current person
        **kwargs: Additional parameters (ignored)
        
    Returns:
        Confirmation of name update
    """
    print(f"[TOOL CALL] update_name_tool(new_name='{new_name}', kwargs={kwargs})")
    
    if not _database_manager:
        error_msg = "Database manager not available"
        print(f"[ERROR] {error_msg}")
        return f"Error: {error_msg}"
    
    if not _current_person_id_getter:
        error_msg = "Person ID getter not available"
        print(f"[ERROR] {error_msg}")
        return f"Error: {error_msg}"
    
    # Get current person_id
    person_id = _current_person_id_getter()
    if not person_id:
        error_msg = "No person currently in conversation"
        print(f"[ERROR] {error_msg}")
        return f"Error: {error_msg}"
    
    try:
        # Update person name using person_id
        _database_manager.update_person_name(person_id, new_name)
        result = f"Updated name to '{new_name}'"
        print(f"[TOOL RESULT] {result}")
        return result
    except ValueError as e:
        error_msg = f"Person not found: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Failed to update name: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return f"Error: {error_msg}"

