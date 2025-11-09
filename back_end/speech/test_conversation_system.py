#!/usr/bin/env python3
"""Comprehensive test script for conversation agent system."""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from speech.conversation.state import ConversationState, Message
from speech.conversation.database import DatabaseManager
from speech.conversation.stream_coordinator import StreamCoordinator, EventType
from speech.conversation.agent import ConversationAgent
from speech.conversation.summarizer import ConversationSummarizer
from speech.conversation.orchestrator import ConversationOrchestrator


class TestConversationState(unittest.TestCase):
    """Test conversation state management."""
    
    def test_create_state(self):
        """Test creating a conversation state."""
        state = ConversationState()
        self.assertIsNotNone(state.conversation_id)
        self.assertEqual(len(state.messages), 0)
        self.assertEqual(len(state.tool_calls), 0)
    
    def test_add_message(self):
        """Test adding messages."""
        state = ConversationState()
        state.add_message("user", "Hello")
        self.assertEqual(len(state.messages), 1)
        self.assertEqual(state.messages[0].role, "user")
        self.assertEqual(state.messages[0].content, "Hello")
        self.assertIsNotNone(state.last_speech_time)
    
    def test_add_tool_call(self):
        """Test adding tool calls."""
        state = ConversationState()
        state.add_tool_call("test_tool", {"arg": "value"}, "result")
        self.assertEqual(len(state.tool_calls), 1)
        self.assertEqual(state.tool_calls[0]["tool"], "test_tool")


class TestDatabaseManager(unittest.TestCase):
    """Test database operations."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        # Skip if DATABASE_URL not set
        if not os.getenv("DATABASE_URL"):
            raise unittest.SkipTest("DATABASE_URL not set, skipping database tests")
        
        cls.db = DatabaseManager()
        try:
            cls.db.initialize_schema()
        except Exception as e:
            print(f"Warning: Could not initialize schema: {e}")
            raise unittest.SkipTest(f"Database setup failed: {e}")
    
    def setUp(self):
        """Clean up before each test."""
        # Note: In production, use transactions and rollback
        pass
    
    def test_add_memory(self):
        """Test adding a memory."""
        memory_id = self.db.add_memory(
            memory_text="Test memory",
            person_id="test_person_1",
            context="Test context",
            conversation_id="test_conv_1"
        )
        self.assertIsNotNone(memory_id)
        self.assertIsInstance(memory_id, int)
    
    def test_get_memories_for_person(self):
        """Test getting memories for a person."""
        # Add a memory
        self.db.add_memory(
            memory_text="Person memory",
            person_id="test_person_2",
            conversation_id="test_conv_2"
        )
        
        # Retrieve memories
        memories = self.db.get_memories_for_person("test_person_2")
        self.assertGreater(len(memories), 0)
        self.assertEqual(memories[0]["person_id"], "test_person_2")
    
    def test_add_todo(self):
        """Test adding a todo."""
        todo_id = self.db.add_todo(
            description="Test todo",
            person_id="test_person_3",
            conversation_id="test_conv_3"
        )
        self.assertIsNotNone(todo_id)
        self.assertIsInstance(todo_id, int)
    
    def test_get_todos(self):
        """Test getting todos."""
        # Add a todo
        self.db.add_todo(
            description="Get todos test",
            status="pending",
            conversation_id="test_conv_4"
        )
        
        # Get todos
        todos = self.db.get_todos(status="pending")
        self.assertGreater(len(todos), 0)
    
    def test_update_todo_status(self):
        """Test updating todo status."""
        # Add a todo
        todo_id = self.db.add_todo(
            description="Update test todo",
            conversation_id="test_conv_5"
        )
        
        # Update status
        self.db.update_todo_status(todo_id, "completed")
        
        # Verify
        todo = self.db.get_todo_by_id(todo_id)
        self.assertEqual(todo["status"], "completed")
        self.assertIsNotNone(todo["completed_at"])


class TestStreamCoordinator(unittest.TestCase):
    """Test stream coordinator."""
    
    def test_speech_event(self):
        """Test speech event emission."""
        events = []
        
        def on_event(event):
            events.append(event)
        
        coordinator = StreamCoordinator(on_event=on_event)
        coordinator.start()
        
        timestamp = datetime.now()
        coordinator.emit_speech_event("Hello", timestamp)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, EventType.SPEECH)
        self.assertEqual(events[0].data["text"], "Hello")


class TestAgent(unittest.TestCase):
    """Test conversation agent."""
    
    @patch('speech.conversation.agent.ChatNVIDIA')
    def test_agent_initialization(self, mock_chat):
        """Test agent initialization."""
        mock_llm = Mock()
        mock_chat.return_value = mock_llm
        
        agent = ConversationAgent()
        self.assertIsNotNone(agent.agent)
        self.assertEqual(len(agent.tools), 1)
    
    @patch('speech.conversation.agent.ChatNVIDIA')
    @patch('speech.conversation.agent.create_react_agent')
    def test_process_utterance(self, mock_create_agent, mock_chat):
        """Test processing an utterance."""
        # Mock LLM
        mock_llm = Mock()
        mock_chat.return_value = mock_llm
        
        # Mock agent
        mock_agent_instance = Mock()
        mock_agent_instance.invoke.return_value = {
            "messages": [Mock(content="Test response")]
        }
        mock_create_agent.return_value = mock_agent_instance
        
        agent = ConversationAgent()
        state = ConversationState()
        
        response = agent.process_utterance("Hello", state)
        
        self.assertIsNotNone(response)
        mock_agent_instance.invoke.assert_called_once()


class TestSummarizer(unittest.TestCase):
    """Test conversation summarizer."""
    
    @patch('speech.conversation.summarizer.ChatNVIDIA')
    def test_summarizer_initialization(self, mock_chat):
        """Test summarizer initialization."""
        mock_llm = Mock()
        mock_chat.return_value = mock_llm
        
        summarizer = ConversationSummarizer()
        self.assertIsNotNone(summarizer.llm)
    
    @patch('speech.conversation.summarizer.ChatNVIDIA')
    def test_generate_summary(self, mock_chat):
        """Test summary generation."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '{"participants": ["unknown"], "key_topics": ["test"], "action_items": [], "tool_calls": [], "summary": "Test summary"}'
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat.return_value = mock_llm
        
        summarizer = ConversationSummarizer()
        state = ConversationState()
        state.add_message("user", "Hello")
        state.add_message("assistant", "Hi there")
        
        summary = summarizer.generate_summary(state)
        
        self.assertIn("participants", summary)
        self.assertIn("summary", summary)
        self.assertEqual(summary["conversation_id"], state.conversation_id)


class TestOrchestrator(unittest.TestCase):
    """Test orchestrator integration."""
    
    @patch('speech.conversation.orchestrator.DatabaseManager')
    @patch('speech.conversation.orchestrator.ConversationAgent')
    @patch('speech.conversation.orchestrator.ConversationSummarizer')
    def test_orchestrator_initialization(self, mock_summarizer, mock_agent, mock_db):
        """Test orchestrator initialization."""
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance
        
        orchestrator = ConversationOrchestrator()
        
        self.assertIsNotNone(orchestrator.conversation_state)
        self.assertIsNotNone(orchestrator.agent)
    
    def test_turn_complete_flow(self):
        """Test complete turn handling flow."""
        with patch('speech.conversation.orchestrator.DatabaseManager') as mock_db:
            mock_db_instance = Mock()
            mock_db.return_value = mock_db_instance
            
            with patch('speech.conversation.orchestrator.ConversationAgent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent.process_utterance.return_value = "Test response"
                mock_agent_class.return_value = mock_agent
                
                orchestrator = ConversationOrchestrator()
                
                # Simulate turn completion
                orchestrator._handle_turn_complete("Hello", datetime.now())
                
                # Verify message was added
                self.assertEqual(len(orchestrator.conversation_state.messages), 2)
                self.assertEqual(orchestrator.conversation_state.messages[0].content, "Hello")
                self.assertEqual(orchestrator.conversation_state.messages[1].content, "Test response")


def run_tests():
    """Run all tests."""
    # Configure test output
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestConversationState))
    
    # Database tests (may be skipped if DB not available)
    try:
        suite.addTests(loader.loadTestsFromTestCase(TestDatabaseManager))
    except unittest.SkipTest:
        print("Skipping database tests (DATABASE_URL not set)")
    
    suite.addTests(loader.loadTestsFromTestCase(TestStreamCoordinator))
    suite.addTests(loader.loadTestsFromTestCase(TestAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestSummarizer))
    suite.addTests(loader.loadTestsFromTestCase(TestOrchestrator))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 70)
    print("Conversation Agent System Test Suite")
    print("=" * 70)
    print()
    
    success = run_tests()
    
    print()
    print("=" * 70)
    if success:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed. Check output above.")
        sys.exit(1)

