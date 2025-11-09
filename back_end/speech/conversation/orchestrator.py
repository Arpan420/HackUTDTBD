"""Main orchestrator for conversation agent system."""

import json
import time
import uuid
from datetime import datetime
from typing import Optional, Callable

from .speech_handler import SpeechHandler
from .face_handler import FaceHandler
from .stream_coordinator import StreamCoordinator, StreamEvent, EventType
from .state import ConversationState
from .agent import ConversationAgent
from .summarizer import ConversationSummarizer
from .database import DatabaseManager
from .tools.notification import set_notification_callback


class ConversationOrchestrator:
    """Main orchestrator that coordinates all components."""
    
    def __init__(
        self,
        end_silence_threshold_seconds: float = 2.0,
        model: str = "nvidia/nvidia-nemotron-nano-9b-v2",
        database_manager: Optional[DatabaseManager] = None
    ):
        """Initialize orchestrator.
        
        Args:
            end_silence_threshold_seconds: Silence threshold for conversation end
            model: LLM model identifier
            database_manager: Optional database manager (creates new one if not provided)
        """
        # Initialize database manager
        self.database_manager = database_manager
        if self.database_manager is None:
            try:
                self.database_manager = DatabaseManager()
            except Exception as e:
                print(f"Warning: Database not available: {e}. Continuing without database.")
                self.database_manager = None
        
        # Initialize state
        self.conversation_state = ConversationState()
        
        # Initialize components
        self.stream_coordinator = StreamCoordinator(on_event=self._handle_stream_event)
        # No turn detector needed - Riva provides is_final flag for turn detection
        self.agent = ConversationAgent(model=model)
        self.summarizer = ConversationSummarizer(
            model=model,
            database_manager=self.database_manager
        )
        
        # Speech handler (will be initialized when audio stream is available)
        self.speech_handler: Optional[SpeechHandler] = None
        
        # Face handler (Phase 2 placeholder)
        self.face_handler = FaceHandler(
            on_person_detected=self._handle_person_detected,
            on_person_lost=self._handle_person_lost
        )
        
        # Callbacks for WebSocket communication
        self.on_notification: Optional[Callable[[str, str], None]] = None
        self.on_person_switch: Optional[Callable[[Optional[str], Optional[str], Optional[str]], None]] = None
        self._previous_person_id: Optional[str] = None
        
        # Running state
        self.is_running = False
        self.summary_generated = False
    
    def set_callbacks(
        self,
        on_notification: Optional[Callable[[str, str], None]] = None,
        on_person_switch: Optional[Callable[[Optional[str], Optional[str], Optional[str]], None]] = None
    ) -> None:
        """Set callbacks for notifications and person switches.
        
        Args:
            on_notification: Callback called with (title, message) when notification tool is used
            on_person_switch: Callback called with (person_id, person_name, recap) when person changes
        """
        self.on_notification = on_notification
        self.on_person_switch = on_person_switch
        
        # Also set notification callback in the tool
        if on_notification:
            set_notification_callback(on_notification)
    
    def initialize_speech_handler(self, **kwargs) -> None:
        """Initialize speech handler with audio stream callback.
        
        Args:
            **kwargs: Arguments to pass to SpeechHandler constructor
        """
        self.speech_handler = SpeechHandler(
            on_transcription=self._handle_speech_transcription,
            **kwargs
        )
        self.speech_handler.connect()
    
    def _handle_speech_transcription(self, text: str, timestamp: datetime) -> None:
        """Handle speech transcription from speech handler.
        
        Args:
            text: Transcribed text
            timestamp: When speech was detected
        """
        # Emit speech event through coordinator
        self.stream_coordinator.emit_speech_event(text, timestamp)
    
    def _handle_speech_transcription_direct(self, text: str, timestamp: datetime) -> None:
        """Direct handler for speech transcription (used by stream coordinator).
        
        When Riva sends a final transcription (is_final=True), it means the turn is complete.
        We immediately send it to the agent.
        
        Args:
            text: Transcribed text (already final from Riva)
            timestamp: When speech was detected
        """
        # Riva already detected turn completion (is_final=True), so process immediately
        self._handle_turn_complete(text, timestamp)
    
    def _handle_stream_event(self, event: StreamEvent) -> None:
        """Handle unified stream event.
        
        Args:
            event: Stream event
        """
        if event.type == EventType.SPEECH:
            text = event.data.get("text", "")
            self._handle_speech_transcription_direct(text, event.timestamp)
        elif event.type == EventType.FACE:
            # Phase 2: Handle face events
            person_id = event.data.get("person_id")
            present = event.data.get("present", False)
            if present and person_id:
                # Check if person changed
                if person_id != self._previous_person_id:
                    self._handle_person_switch(person_id)
                self.conversation_state.current_person_id = person_id
                self.conversation_state.person_present = True
            else:
                self.conversation_state.person_present = False
    
    def _handle_turn_complete(self, utterance: str, timestamp: datetime) -> None:
        """Handle completed user turn.
        
        Args:
            utterance: Complete user utterance
            timestamp: When turn was completed
        """
        # Add user message to state
        person_id = self.conversation_state.current_person_id
        self.conversation_state.add_message("user", utterance, person_id=person_id)
        
        # Pass to agent
        agent_response = self.agent.process_utterance(utterance, self.conversation_state)
        
        # Only add agent response to state if it's not [NO FURTHER RESPONSE]
        # [NO FURTHER RESPONSE] is an internal signal and shouldn't be stored
        if agent_response != "[NO FURTHER RESPONSE]":
            self.conversation_state.add_message("assistant", agent_response)
            print(f"User: {utterance}")
            print(f"Agent: {agent_response}")
        else:
            print(f"User: {utterance}")
            print(f"Agent: [NO FURTHER RESPONSE] (not stored in conversation history)")
    
    def _handle_person_detected(self, person_id: str, timestamp: datetime) -> None:
        """Handle person detection (Phase 2).
        
        Args:
            person_id: Detected person ID
            timestamp: When person was detected
        """
        # Check if person changed
        if person_id != self._previous_person_id:
            self._handle_person_switch(person_id)
        self.conversation_state.current_person_id = person_id
        self.conversation_state.person_present = True
    
    def _handle_person_switch(self, person_id: Optional[str]) -> None:
        """Handle person switch event.
        
        Args:
            person_id: New person ID (or None if person lost/"nobody")
        """
        previous_person_id = self._previous_person_id
        
        # If switching to "nobody", do nothing
        if person_id is None:
            self._previous_person_id = None
            return
        
        # If previous person had messages, summarize their conversation
        if previous_person_id and self.database_manager:
            try:
                # Filter messages for the previous person
                previous_messages = [
                    msg for msg in self.conversation_state.messages
                    if msg.person_id == previous_person_id
                ]
                
                if previous_messages:
                    print(f"[Orchestrator] Summarizing conversation for {previous_person_id}")
                    
                    # Create a temporary conversation state with only previous person's messages
                    from .state import ConversationState
                    temp_state = ConversationState()
                    temp_state.messages = previous_messages
                    temp_state.conversation_id = self.conversation_state.conversation_id
                    temp_state.current_person_id = previous_person_id
                    
                    # Generate and save summary
                    summary_text = self.summarizer.generate_and_save_summary(
                        temp_state,
                        previous_person_id
                    )
                    
                    # Update faces table with recap (latest summary)
                    if summary_text:
                        try:
                            self.database_manager.create_or_update_face(
                                person_id=previous_person_id,
                                recap=summary_text
                            )
                        except Exception as e:
                            print(f"Warning: Failed to update face recap: {e}")
            except Exception as e:
                print(f"Warning: Failed to summarize previous person's conversation: {e}")
                import traceback
                traceback.print_exc()
        
        # Update previous person ID
        self._previous_person_id = person_id
        
        # Check if person exists in database
        person_exists = False
        person_name = None
        recap = None
        
        if self.database_manager:
            try:
                person_exists = self.database_manager.person_exists(person_id)
                
                # Get person name
                person_name = self.database_manager.get_person_name(person_id)
                if not person_name:
                    person_name = person_id  # Fallback to person_id as name
                
                # If person exists, get their recap
                if person_exists:
                    recap = self.database_manager.get_latest_summary(person_id)
            except Exception as e:
                print(f"Warning: Failed to check person existence: {e}")
        
        # If switching to new person, create new conversation thread
        if not person_exists:
            self.conversation_state.conversation_id = str(uuid.uuid4())
            print(f"[Orchestrator] Created new conversation thread for new person: {person_id}")
        
        # If person exists, send notification with name and recap
        if person_exists and self.on_notification and recap:
            try:
                self.on_notification(
                    f"Switching to {person_name}",
                    recap
                )
            except Exception as e:
                print(f"Error sending notification: {e}")
        
        # Call person switch callback if set
        if self.on_person_switch:
            try:
                self.on_person_switch(person_id, person_name, recap)
            except Exception as e:
                print(f"Error in person switch callback: {e}")
    
    def _handle_person_lost(self, person_id: str, timestamp: datetime) -> None:
        """Handle person loss (Phase 2).
        
        Args:
            person_id: Lost person ID
            timestamp: When person was lost
        """
        self.conversation_state.person_present = False
    
    def _handle_conversation_end(self, conversation_state: ConversationState) -> None:
        """Handle conversation end.
        
        Args:
            conversation_state: Final conversation state
        """
        if self.summary_generated:
            return
        
        self.summary_generated = True
        print("\n=== Conversation Ended ===")
        print("Generating summary...")
        
        # Generate summary
        summary = self.summarizer.generate_summary(conversation_state)
        
        # Print summary
        print("\n=== Conversation Summary ===")
        print(json.dumps(summary, indent=2))
        
        # Save summary (could save to file/database here)
        # TODO: Save to PostgreSQL database
    
    def process_audio_chunk(self, audio_data: bytes) -> None:
        """Process audio chunk from AR glasses device.
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM, mono)
        """
        if self.speech_handler:
            self.speech_handler.process_audio_chunk(audio_data)
    
    def start(self) -> None:
        """Start the orchestrator."""
        self.is_running = True
        self.stream_coordinator.start()
        self.face_handler.start()
        
        if self.speech_handler:
            self.speech_handler.start_streaming()
    
    def run(self) -> None:
        """Run the main event loop."""
        self.start()
        
        try:
            while self.is_running:
                # No need to check turn detector - Riva handles turn detection via is_final
                
                # Small sleep to avoid busy waiting
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping orchestrator...")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the orchestrator."""
        self.is_running = False
        
        if self.speech_handler:
            self.speech_handler.stop_streaming()
            self.speech_handler.disconnect()
        
        self.stream_coordinator.stop()
        self.face_handler.stop()
        
        # Generate final summary if conversation had messages
        if self.conversation_state.messages and not self.summary_generated:
            self._handle_conversation_end(self.conversation_state)
        
        # Close database connection
        if self.database_manager:
            self.database_manager.close()
        
        # Note: ESP32 stream integration placeholder
        # In the future, ESP32 will maintain the current interaction ID
        # For now, interaction ID is maintained in conversation_state.conversation_id

