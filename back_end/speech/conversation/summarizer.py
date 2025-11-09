"""Conversation summary generation."""

import json
from typing import Dict, Any, List, Optional
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from dotenv import load_dotenv

from .state import ConversationState
from .database import DatabaseManager

load_dotenv()


class ConversationSummarizer:
    """Generates structured summaries of conversations."""
    
    def __init__(
        self,
        model: str = "nvidia/nvidia-nemotron-nano-9b-v2",
        database_manager: Optional[DatabaseManager] = None
    ):
        """Initialize summarizer.
        
        Args:
            model: LLM model identifier
            database_manager: Optional database manager for saving memories and todos
        """
        self.llm = ChatNVIDIA(
            model=model,
            temperature=0.3,
            max_tokens=2048
        )
        self.database_manager = database_manager
    
    def generate_summary(self, conversation_state: ConversationState) -> Dict[str, Any]:
        """Generate structured summary of conversation.
        
        Args:
            conversation_state: Conversation state to summarize
            
        Returns:
            Dictionary with summary fields
        """
        # Build conversation text
        conversation_text = self._build_conversation_text(conversation_state)
        
        # Create summary prompt
        prompt = f"""Generate a structured summary of the following conversation.

Conversation:
{conversation_text}

Provide a JSON summary with the following structure:
{{
    "participants": ["list of person_ids or 'unknown' if not available"],
    "key_topics": ["list of main topics discussed"],
    "action_items": ["list of any action items or decisions made"],
    "tool_calls": ["list of tools that were used"],
    "summary": "brief overall summary of the conversation"
}}

Return only valid JSON, no additional text."""

        try:
            response = self.llm.invoke(prompt)
            print(f"[Summarizer] Summary responded: LLM returned response for conversation {conversation_state.conversation_id}")
            
            # Extract JSON from response
            if hasattr(response, "content"):
                content = response.content
            else:
                content = str(response)
            
            # Try to parse JSON
            try:
                # Extract JSON from markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                summary = json.loads(content)
            except json.JSONDecodeError:
                # Fallback: create summary from text
                summary = {
                    "participants": self._extract_participants(conversation_state),
                    "key_topics": [],
                    "action_items": [],
                    "tool_calls": [tc["tool"] for tc in conversation_state.tool_calls],
                    "summary": content
                }
            
            # Add metadata
            summary["conversation_id"] = conversation_state.conversation_id
            summary["message_count"] = len(conversation_state.messages)
            summary["tool_call_count"] = len(conversation_state.tool_calls)
            
            # Save memories and todos to database if available
            if self.database_manager:
                self._save_to_database(summary, conversation_state)
            
            return summary
        except Exception as e:
            # Fallback summary
            return {
                "participants": self._extract_participants(conversation_state),
                "key_topics": [],
                "action_items": [],
                "tool_calls": [tc["tool"] for tc in conversation_state.tool_calls],
                "summary": f"Error generating summary: {str(e)}",
                "conversation_id": conversation_state.conversation_id,
                "message_count": len(conversation_state.messages),
                "tool_call_count": len(conversation_state.tool_calls)
            }
    
    def generate_and_save_summary(
        self,
        conversation_state: ConversationState,
        person_id: str
    ) -> Optional[str]:
        """Generate summary and save it to the summaries table.
        
        Args:
            conversation_state: Conversation state to summarize
            person_id: Person ID to associate with the summary
            
        Returns:
            Summary text if successful, None otherwise
        """
        print(f"[Summarizer] Summary triggered: Generating summary for person {person_id}, conversation {conversation_state.conversation_id}")
        
        if not self.database_manager:
            print("Warning: Database manager not available, cannot save summary")
            return None
        
        try:
            # Generate summary
            summary_dict = self.generate_summary(conversation_state)
            
            # Extract summary text (use the "summary" field from the dict)
            summary_text = summary_dict.get("summary", "")
            if not summary_text:
                # Fallback: create a text representation of the summary
                summary_text = json.dumps(summary_dict, indent=2)
            
            # Save to database (logging handled in database.py)
            self.database_manager.add_summary(person_id, summary_text)
            
            print(f"[Summarizer] Saved summary for person {person_id}")
            return summary_text
        except Exception as e:
            print(f"Warning: Failed to generate and save summary: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_conversation_text(self, conversation_state: ConversationState) -> str:
        """Build text representation of conversation.
        
        Args:
            conversation_state: Conversation state
            
        Returns:
            Formatted conversation text
        """
        lines = []
        for msg in conversation_state.messages:
            person_info = f" [{msg.person_id}]" if msg.person_id else ""
            lines.append(f"{msg.role.upper()}{person_info}: {msg.content}")
        return "\n".join(lines)
    
    def _extract_participants(self, conversation_state: ConversationState) -> List[str]:
        """Extract unique participant IDs from conversation.
        
        Args:
            conversation_state: Conversation state
            
        Returns:
            List of participant IDs (or ["unknown"] if none)
        """
        participants = set()
        for msg in conversation_state.messages:
            if msg.person_id:
                participants.add(msg.person_id)
        
        if participants:
            return list(participants)
        else:
            return ["unknown"]
    
    def _save_to_database(
        self,
        summary: Dict[str, Any],
        conversation_state: ConversationState
    ) -> None:
        """Save memories and todos from summary to database.
        
        Args:
            summary: Generated summary dictionary
            conversation_state: Conversation state
        """
        if not self.database_manager:
            return
        
        conversation_id = conversation_state.conversation_id
        
        try:
            # Save memories
            if "key_topics" in summary:
                for topic in summary["key_topics"]:
                    if topic and isinstance(topic, str):
                        person_id = conversation_state.current_person_id
                        self.database_manager.add_memory(
                            memory_text=topic,
                            person_id=person_id,
                            context="Extracted from conversation summary",
                            conversation_id=conversation_id
                        )
            
            # Save todos/action items
            if "action_items" in summary:
                for action_item in summary["action_items"]:
                    if action_item and isinstance(action_item, str):
                        person_id = conversation_state.current_person_id
                        self.database_manager.add_todo(
                            description=action_item,
                            person_id=person_id,
                            conversation_id=conversation_id,
                            status="pending"
                        )
        except Exception as e:
            # Log error but don't fail summary generation
            print(f"Warning: Failed to save to database: {e}")

