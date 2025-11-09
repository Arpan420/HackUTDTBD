#!/usr/bin/env python3
"""Comprehensive test script for summary function edge cases."""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from speech.conversation.state import ConversationState, Message
from speech.conversation.database import DatabaseManager
from speech.conversation.summarizer import ConversationSummarizer


class TestSummaryEdgeCases(unittest.TestCase):
    """Test summary function with various edge cases."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database if available."""
        cls.db = None
        if os.getenv("DATABASE_URL"):
            try:
                cls.db = DatabaseManager()
                cls.db.initialize_schema()
            except Exception as e:
                print(f"Warning: Could not initialize database: {e}")
                cls.db = None
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock LLM response for predictable testing
        self.mock_llm_response = {
            "participants": ["test_person"],
            "key_topics": ["test topic"],
            "action_items": ["test action"],
            "tool_calls": [],
            "summary": "Test conversation summary"
        }
    
    @patch('speech.conversation.summarizer.ChatNVIDIA')
    def test_empty_conversation(self, mock_chat):
        """Test summary generation with empty conversation state (no messages)."""
        # Mock LLM
        mock_response = Mock()
        mock_response.content = '{"participants": ["unknown"], "key_topics": [], "action_items": [], "tool_calls": [], "summary": "Empty conversation"}'
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat.return_value = mock_llm
        
        summarizer = ConversationSummarizer(database_manager=self.db)
        state = ConversationState()
        # No messages added
        
        summary = summarizer.generate_summary(state)
        
        self.assertIn("participants", summary)
        self.assertIn("summary", summary)
        self.assertEqual(len(state.messages), 0)
        self.assertEqual(summary["message_count"], 0)
    
    @patch('speech.conversation.summarizer.ChatNVIDIA')
    def test_no_person_id_in_messages(self, mock_chat):
        """Test summary generation when person_id is None in all messages."""
        # Mock LLM
        mock_response = Mock()
        mock_response.content = '{"participants": ["unknown"], "key_topics": ["topic"], "action_items": [], "tool_calls": [], "summary": "Conversation with no person ID"}'
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat.return_value = mock_llm
        
        summarizer = ConversationSummarizer(database_manager=self.db)
        state = ConversationState()
        state.add_message("user", "Hello", person_id=None)
        state.add_message("assistant", "Hi there", person_id=None)
        
        summary = summarizer.generate_summary(state)
        
        self.assertIn("participants", summary)
        # Should include "unknown" since no person_id
        self.assertIn("unknown", summary["participants"])
    
    @patch('speech.conversation.summarizer.ChatNVIDIA')
    def test_generate_and_save_no_person_id(self, mock_chat):
        """Test generate_and_save_summary with person_id parameter (should work)."""
        if not self.db:
            self.skipTest("Database not available")
        
        # Mock LLM
        mock_response = Mock()
        mock_response.content = '{"participants": ["test_person"], "key_topics": [], "action_items": [], "tool_calls": [], "summary": "Test summary"}'
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat.return_value = mock_llm
        
        summarizer = ConversationSummarizer(database_manager=self.db)
        state = ConversationState()
        state.add_message("user", "Hello")
        state.add_message("assistant", "Hi")
        
        # This should work even if messages don't have person_id
        # because we pass person_id as parameter
        summary_text = summarizer.generate_and_save_summary(state, "test_person_1")
        
        self.assertIsNotNone(summary_text)
        self.assertIn("Test summary", summary_text)
    
    @patch('speech.conversation.summarizer.ChatNVIDIA')
    def test_person_not_in_database(self, mock_chat):
        """Test behavior when person_id exists in conversation but not in database."""
        if not self.db:
            self.skipTest("Database not available")
        
        # Mock LLM
        mock_response = Mock()
        mock_response.content = '{"participants": ["unknown_person"], "key_topics": [], "action_items": [], "tool_calls": [], "summary": "Summary for unknown person"}'
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat.return_value = mock_llm
        
        summarizer = ConversationSummarizer(database_manager=self.db)
        state = ConversationState()
        state.add_message("user", "Hello", person_id="unknown_person")
        
        # Person doesn't exist in database, but summary should still be generated
        summary = summarizer.generate_summary(state)
        
        self.assertIsNotNone(summary)
        self.assertIn("summary", summary)
        
        # Should be able to save summary even if person doesn't exist in faces table
        summary_text = summarizer.generate_and_save_summary(state, "unknown_person")
        self.assertIsNotNone(summary_text)
    
    @patch('speech.conversation.summarizer.ChatNVIDIA')
    def test_no_database_manager(self, mock_chat):
        """Test summary generation when database manager is None."""
        # Mock LLM
        mock_response = Mock()
        mock_response.content = '{"participants": ["test"], "key_topics": [], "action_items": [], "tool_calls": [], "summary": "Summary without DB"}'
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat.return_value = mock_llm
        
        # Create summarizer without database manager
        summarizer = ConversationSummarizer(database_manager=None)
        state = ConversationState()
        state.add_message("user", "Hello")
        
        # Should still generate summary
        summary = summarizer.generate_summary(state)
        self.assertIsNotNone(summary)
        
        # But generate_and_save_summary should return None
        summary_text = summarizer.generate_and_save_summary(state, "test_person")
        self.assertIsNone(summary_text)
    
    @patch('speech.conversation.summarizer.ChatNVIDIA')
    def test_multiple_summaries_same_person(self, mock_chat):
        """Test multiple summaries for the same person."""
        if not self.db:
            self.skipTest("Database not available")
        
        # Mock LLM
        mock_response = Mock()
        mock_response.content = '{"participants": ["person_1"], "key_topics": [], "action_items": [], "tool_calls": [], "summary": "Summary"}'
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat.return_value = mock_llm
        
        summarizer = ConversationSummarizer(database_manager=self.db)
        person_id = "test_person_multi"
        
        # Create first summary
        state1 = ConversationState()
        state1.add_message("user", "First conversation")
        summary1 = summarizer.generate_and_save_summary(state1, person_id)
        
        # Create second summary
        state2 = ConversationState()
        state2.add_message("user", "Second conversation")
        summary2 = summarizer.generate_and_save_summary(state2, person_id)
        
        self.assertIsNotNone(summary1)
        self.assertIsNotNone(summary2)
        
        # Get latest summary should return the second one
        latest = self.db.get_latest_summary(person_id)
        self.assertIsNotNone(latest)
        # Should contain content from second summary
        self.assertIn("Summary", latest)
    
    @patch('speech.conversation.summarizer.ChatNVIDIA')
    def test_only_user_messages(self, mock_chat):
        """Test summary with only user messages (no assistant responses)."""
        # Mock LLM
        mock_response = Mock()
        mock_response.content = '{"participants": ["user"], "key_topics": [], "action_items": [], "tool_calls": [], "summary": "Only user messages"}'
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat.return_value = mock_llm
        
        summarizer = ConversationSummarizer(database_manager=self.db)
        state = ConversationState()
        state.add_message("user", "Hello")
        state.add_message("user", "How are you?")
        # No assistant messages
        
        summary = summarizer.generate_summary(state)
        
        self.assertIn("participants", summary)
        self.assertEqual(summary["message_count"], 2)
        # All messages should be user messages
        self.assertTrue(all(msg.role == "user" for msg in state.messages))
    
    @patch('speech.conversation.summarizer.ChatNVIDIA')
    def test_llm_json_decode_error(self, mock_chat):
        """Test handling when LLM returns invalid JSON."""
        # Mock LLM returning non-JSON response
        mock_response = Mock()
        mock_response.content = "This is not valid JSON"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat.return_value = mock_llm
        
        summarizer = ConversationSummarizer(database_manager=self.db)
        state = ConversationState()
        state.add_message("user", "Hello")
        
        # Should handle gracefully with fallback
        summary = summarizer.generate_summary(state)
        
        self.assertIn("summary", summary)
        # Should use the raw content as summary text
        self.assertIn("This is not valid JSON", summary["summary"])
        # Should still have participants extracted
        self.assertIn("participants", summary)
    
    @patch('speech.conversation.summarizer.ChatNVIDIA')
    def test_llm_exception(self, mock_chat):
        """Test handling when LLM raises an exception."""
        # Mock LLM raising exception
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM service unavailable")
        mock_chat.return_value = mock_llm
        
        summarizer = ConversationSummarizer(database_manager=self.db)
        state = ConversationState()
        state.add_message("user", "Hello")
        
        # Should handle gracefully with error summary
        summary = summarizer.generate_summary(state)
        
        self.assertIn("summary", summary)
        self.assertIn("Error generating summary", summary["summary"])
        self.assertIn("participants", summary)
    
    def test_update_person_recap(self):
        """Test updating person recap/description via create_or_update_face()."""
        if not self.db:
            self.skipTest("Database not available")
        
        person_id = "test_person_recap"
        recap_text = "This is a test recap for the person"
        
        # Create or update face with recap
        self.db.create_or_update_face(
            person_id=person_id,
            recap=recap_text
        )
        
        # Verify recap was saved
        face = self.db.get_face_by_person_id(person_id)
        self.assertIsNotNone(face)
        self.assertEqual(face["recap"], recap_text)
        
        # Update recap
        new_recap = "Updated recap text"
        self.db.create_or_update_face(
            person_id=person_id,
            recap=new_recap
        )
        
        # Verify recap was updated
        face = self.db.get_face_by_person_id(person_id)
        self.assertEqual(face["recap"], new_recap)
    
    def test_get_latest_summary_nonexistent_person(self):
        """Test getting latest summary for person that doesn't exist."""
        if not self.db:
            self.skipTest("Database not available")
        
        # Should return None, not raise exception
        summary = self.db.get_latest_summary("nonexistent_person_12345")
        self.assertIsNone(summary)
    
    def test_add_summary_with_tool_calls(self):
        """Test summary generation with tool calls in conversation state."""
        if not self.db:
            self.skipTest("Database not available")
        
        with patch('speech.conversation.summarizer.ChatNVIDIA') as mock_chat:
            # Mock LLM
            mock_response = Mock()
            mock_response.content = '{"participants": ["test"], "key_topics": [], "action_items": [], "tool_calls": ["web_search", "notification"], "summary": "Summary with tool calls"}'
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_chat.return_value = mock_llm
            
            summarizer = ConversationSummarizer(database_manager=self.db)
            state = ConversationState()
            state.add_message("user", "Hello")
            state.add_tool_call("web_search", {"query": "test"}, "results")
            state.add_tool_call("notification", {"title": "Test"}, None)
            
            summary = summarizer.generate_summary(state)
            
            self.assertIn("tool_calls", summary)
            self.assertEqual(summary["tool_call_count"], 2)


def run_tests():
    """Run all edge case tests."""
    # Configure test output
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test class
    suite.addTests(loader.loadTestsFromTestCase(TestSummaryEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 70)
    print("Summary Function Edge Cases Test Suite")
    print("=" * 70)
    print()
    
    success = run_tests()
    
    print()
    print("=" * 70)
    if success:
        print("All edge case tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed. Check output above.")
        sys.exit(1)

