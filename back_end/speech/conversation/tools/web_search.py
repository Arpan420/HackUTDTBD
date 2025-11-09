"""Web search tool for research agent."""

import os
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv

load_dotenv()


@tool
def web_search(query: str) -> str:
    """Search the web for information.
    
    Use this tool to search the internet for current information, facts, 
    news, or any other information that requires up-to-date data.
    
    Args:
        query: The search query to execute
        
    Returns:
        Search results as a string
    """
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            error_msg = "TAVILY_API_KEY environment variable not set"
            print(f"[TOOL ERROR] {error_msg}")
            return error_msg
        
        search = TavilySearchResults(tavily_api_key=api_key, max_results=5)
        results = search.run(query)
        
        print(f"[TOOL CALL] web_search(query='{query}')")
        print(f"[TOOL RESULT] {results[:200]}...")  # Print first 200 chars
        
        return results
    except Exception as e:
        error_msg = f"Error performing web search: {str(e)}"
        print(f"[TOOL ERROR] {error_msg}")
        return error_msg

