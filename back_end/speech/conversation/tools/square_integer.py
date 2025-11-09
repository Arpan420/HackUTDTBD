"""Placeholder tool for testing agent tool calling."""

from langchain.tools import tool


@tool
def square_integer(n: int) -> int:
    """Square an integer.
    
    This is a placeholder tool for testing agent tool calling capabilities.
    In production, this would be replaced with real external API tools.
    
    Args:
        n: The integer to square
        
    Returns:
        The square of n (n * n)
    """
    return n * n

