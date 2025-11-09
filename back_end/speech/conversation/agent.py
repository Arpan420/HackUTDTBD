"""LangGraph agent setup for conversation handling."""

import os
from typing import List, Any
from dotenv import load_dotenv

from langgraph.prebuilt import create_react_agent
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .tools.square_integer import square_integer
from .state import ConversationState

# Load environment variables
load_dotenv()

# System prompt for the agent
SYSTEM_PROMPT = (
    "You are a helpful conversation assistant for AR glasses.\n"
    "- You can help users with questions and tasks.\n"
    "- You have access to tools that you can use when needed.\n"
    "- Always be concise and conversational in your responses.\n"
    "- If you use a tool, explain what you did and why.\n"
)


class ConversationAgent:
    """LangGraph agent for handling conversations."""
    
    def __init__(self, model: str = "nvidia/nvidia-nemotron-nano-9b-v2"):
        """Initialize conversation agent.
        
        Args:
            model: LLM model identifier
        """
        # Initialize LLM
        self.llm = ChatNVIDIA(
            model=model,
            temperature=0.6,
            top_p=0.95,
            max_tokens=8192
        )
        
        # Create tools list
        self.tools = [square_integer]
        
        # Create agent graph
        # Note: create_react_agent doesn't have state_modifier parameter
        # We'll add system message to messages instead
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
                messages_modifier=SYSTEM_PROMPT
            )
    
    def process_utterance(
        self,
        utterance: str,
        conversation_state: ConversationState
    ) -> str:
        """Process a user utterance and generate response.
        
        Args:
            utterance: User's spoken text
            conversation_state: Current conversation state
            
        Returns:
            Agent's response text
        """
        # Build message history from conversation state
        # Start with system message
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        for msg in conversation_state.messages:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        # Add current user utterance
        messages.append(HumanMessage(content=utterance))
        
        # Invoke agent
        try:
            response = self.agent.invoke({"messages": messages})
            
            # Extract agent response
            if isinstance(response, dict) and "messages" in response:
                last_message = response["messages"][-1]
                if hasattr(last_message, "content"):
                    agent_response = last_message.content
                else:
                    agent_response = str(last_message)
            else:
                agent_response = str(response)
            
            # Track tool calls if any
            if isinstance(response, dict) and "messages" in response:
                for msg in response["messages"]:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            conversation_state.add_tool_call(
                                tool_name=tool_call.get("name", "unknown"),
                                args=tool_call.get("args", {}),
                                result="executed"
                            )
            
            return agent_response
        except Exception as e:
            return f"I encountered an error: {str(e)}"

