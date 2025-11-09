"""LangGraph agent setup for conversation handling with routing logic."""

import os
from typing import List, Any, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from langgraph.prebuilt import create_react_agent
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .tools import calendar_tool, todo_tool, notification_tool, web_search
from .state import ConversationState

# Load environment variables
load_dotenv()


def get_system_prompt() -> str:
    """Get system prompt with current time from file."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get the directory where this file is located
    current_dir = Path(__file__).parent
    prompt_file = current_dir / "system_prompt.txt"
    
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # Replace {current_time} placeholder
        prompt = prompt_template.format(current_time=current_time)
        return prompt
    except FileNotFoundError:
        # Fallback if file doesn't exist
        return f"You are a minimal, non-intrusive assistant for AR glasses.\nCURRENT TIME: {current_time}\n"
    except Exception as e:
        print(f"[WARNING] Error reading system prompt file: {e}")
        return f"You are a minimal, non-intrusive assistant for AR glasses.\nCURRENT TIME: {current_time}\n"


class ConversationAgent:
    """LangGraph agent for handling conversations with routing logic."""
    
    def __init__(self, model: str = "nvidia/nvidia-nemotron-nano-9b-v2"):
        """Initialize conversation agent.
        
        Args:
            model: LLM model identifier
        """
        # Initialize LLM
        self.llm = ChatNVIDIA(
            model=model,
        )
        
        # Create tools list (web_search, calendar, todo, notification)
        self.tools = [web_search, calendar_tool, todo_tool, notification_tool]
        
        # Create agent graph - LangGraph will automatically handle tool calls
        try:
            self.agent = create_react_agent(
                model=self.llm,
                tools=self.tools
            )
        except TypeError:
            # Fallback: try with messages_modifier if that's the correct parameter
            self.agent = create_react_agent(
                model=self.llm,
                tools=self.tools,
                messages_modifier=get_system_prompt()
            )
    
    def process_utterance(
        self,
        utterance: str,
        conversation_state: ConversationState
    ) -> str:
        """Process a user utterance with routing logic.
        
        Args:
            utterance: User's spoken text
            conversation_state: Current conversation state
            
        Returns:
            Agent's response text (or [NO FURTHER RESPONSE])
        """
        # Log human message
        print(f"[HUMAN] {utterance}")
        
        # Build message history from conversation state
        messages = [SystemMessage(content=get_system_prompt())]
        
        for msg in conversation_state.messages:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        # Add current user utterance
        messages.append(HumanMessage(content=utterance))
        
        # Invoke agent - LangGraph automatically handles tool calls
        try:
            response = self.agent.invoke({"messages": messages})
            
            # Extract information from response
            agent_response = ""
            tool_was_called = False
            agent_reasoning = ""
            
            if isinstance(response, dict) and "messages" in response:
                # Track tool calls first
                for msg in response["messages"]:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        tool_was_called = True
                        for tool_call in msg.tool_calls:
                            if isinstance(tool_call, dict):
                                tool_name = tool_call.get("name", "unknown")
                                tool_args = tool_call.get("args", {})
                            else:
                                tool_name = getattr(tool_call, "name", "unknown")
                                tool_args = getattr(tool_call, "args", {})
                            
                            # Full tool call logging
                            print(f"[TOOL CALL] {tool_name}({tool_args})")
                            conversation_state.add_tool_call(
                                tool_name=tool_name,
                                args=tool_args,
                                result="executed"
                            )
                
                # Log only the FINAL agent reasoning (last AIMessage with content, no tool calls)
                for msg in reversed(response["messages"]):
                    if isinstance(msg, AIMessage) and hasattr(msg, "content") and msg.content:
                        # Only log if this is a final reasoning (no tool calls in this message)
                        if not (hasattr(msg, "tool_calls") and msg.tool_calls):
                            reasoning = msg.content.strip()
                            if reasoning and reasoning not in ["None", "null", ""]:
                                print(f"[AGENT REASONING] {reasoning}")
                                break  # Only log the last one
                
                # Find final agent response (last AIMessage with content)
                for msg in reversed(response["messages"]):
                    if isinstance(msg, AIMessage) and hasattr(msg, "content") and msg.content:
                        agent_response = msg.content
                        break
                
                if not agent_response:
                    last_msg = response["messages"][-1]
                    agent_response = str(last_msg) if last_msg else ""
            
            # If tool was called (especially notification_tool with return_direct), return empty
            if tool_was_called:
                return "[NO FURTHER RESPONSE]"
            
            # Only return response if it's not empty
            if agent_response and len(agent_response.strip()) > 0:
                return agent_response
            
            return "[NO FURTHER RESPONSE]"
            
        except Exception as e:
            error_msg = f"Error in agent processing: {str(e)}"
            print(f"[MAIN AGENT ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            return "[NO FURTHER RESPONSE]"

