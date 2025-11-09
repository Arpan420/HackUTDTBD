"""Update name tool for updating person names."""

from langchain.tools import tool
from typing import Dict, Any, Optional
from ..database import DatabaseManager


# Global database manager reference
_database_manager: Optional[DatabaseManager] = None


def set_database_manager(database_manager: Optional[DatabaseManager]) -> None:
    """Set the database manager to be used by the update_name tool.
    
    Args:
        database_manager: Database manager instance
    """
    global _database_manager
    _database_manager = database_manager


@tool(return_direct=True)
def update_name_tool(person_name: str, new_name: str, **kwargs: Any) -> str:
    """Update a person's name in the database.
    
    This tool updates the person_name field in the faces table.
    It ends the conversation turn after execution (similar to notification_tool).
    
    Args:
        person_name: Current person name to match
        new_name: New name to set
        **kwargs: Additional parameters (ignored)
        
    Returns:
        Confirmation of name update
    """
    print(f"[TOOL CALL] update_name_tool(person_name='{person_name}', new_name='{new_name}', kwargs={kwargs})")
    
    if not _database_manager:
        error_msg = "Database manager not available"
        print(f"[ERROR] {error_msg}")
        return f"Error: {error_msg}"
    
    try:
        # Update person name by matching person_name
        _database_manager.update_person_name_by_name(person_name, new_name)
        result = f"Updated name from '{person_name}' to '{new_name}'"
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

