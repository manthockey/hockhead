"""
Tests for the MessageSanitizer class.

This module contains unit tests for the MessageSanitizer class,
focusing on message filtering and text sanitization.
"""

import pytest
from ai_avatar.sanitizer import MessageSanitizer


class TestMessageSanitizer:
    """Test suite for the MessageSanitizer class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.bot_name = "testbot"
        self.bot_username = "testbot"
        self.banned_words = ["badword", "inappropriate"]
        self.sanitizer = MessageSanitizer(
            bot_name=self.bot_name,
            respond_to_prefix=True,
            respond_to_questions=True,
            banned_words=self.banned_words,
            max_response_chars=50
        )

    def test_should_respond_to_bot_mention_prefix(self):
        """Test that messages with bot name prefix trigger a response."""
        assert self.sanitizer.should_respond_to(f"{self.bot_name}: hello", "user1", self.bot_username)
        assert self.sanitizer.should_respond_to(f"@{self.bot_name} hello", "user1", self.bot_username)
        assert self.sanitizer.should_respond_to(f"!{self.bot_name} hello", "user1", self.bot_username)
        assert self.sanitizer.should_respond_to(f"hey {self.bot_name} hello", "user1", self.bot_username)

    def test_should_respond_to_bot_mention_anywhere(self):
        """Test that messages with bot name anywhere trigger a response."""
        assert self.sanitizer.should_respond_to(f"hello {self.bot_name} how are you", "user1", self.bot_username)
        assert self.sanitizer.should_respond_to(f"can {self.bot_name} help me", "user1", self.bot_username)

    def test_should_respond_to_question(self):
        """Test that questions trigger a response."""
        assert self.sanitizer.should_respond_to("What time is it?", "user1", self.bot_username)
        assert self.sanitizer.should_respond_to("Can you help me?", "user1", self.bot_username)

    def test_should_not_respond_to_own_messages(self):
        """Test that bot doesn't respond to its own messages."""
        assert not self.sanitizer.should_respond_to("Hello everyone!", self.bot_username, self.bot_username)

    def test_should_not_respond_to_banned_words(self):
        """Test that messages with banned words are ignored."""
        assert not self.sanitizer.should_respond_to(f"Hey {self.bot_name}, this contains a badword", "user1", self.bot_username)
        assert not self.sanitizer.should_respond_to("Is this inappropriate?", "user1", self.bot_username)

    def test_should_not_respond_without_trigger(self):
        """Test that messages without triggers are ignored."""
        # Create sanitizer with both triggers disabled
        sanitizer = MessageSanitizer(
            bot_name=self.bot_name,
            respond_to_prefix=False,
            respond_to_questions=False,
            banned_words=self.banned_words
        )
        assert not sanitizer.should_respond_to("Hello everyone", "user1", self.bot_username)
        assert not sanitizer.should_respond_to("What time is it?", "user1", self.bot_username)

    def test_sanitize_response_removes_role_prefix(self):
        """Test that role prefixes are removed from responses."""
        assert self.sanitizer.sanitize_response("Assistant: Hello there") == "Hello there."
        assert self.sanitizer.sanitize_response("Bot: How are you?") == "How are you?"
        assert self.sanitizer.sanitize_response("Avatar: I'm good!") == "I'm good!"

    def test_sanitize_response_trims_long_text(self):
        """Test that long responses are trimmed."""
        long_text = "This is a very long response that exceeds the maximum character limit set for the sanitizer. It should be trimmed."
        sanitized = self.sanitizer.sanitize_response(long_text)
        assert len(sanitized) <= self.sanitizer.max_response_chars + 3  # +3 for possible ellipsis
        assert sanitized.endswith(".")

    def test_sanitize_response_handles_emotes(self):
        """Test that Twitch emotes are handled properly."""
        assert "kappa emote" in self.sanitizer.sanitize_response("That's funny Kappa")
        assert "pog champ emote" in self.sanitizer.sanitize_response("That's amazing PogChamp")

    def test_sanitize_response_handles_emoticons(self):
        """Test that emoticons are handled properly."""
        assert "smiling" in self.sanitizer.sanitize_response("Hello :)")
        assert "sad face" in self.sanitizer.sanitize_response("That's unfortunate :(")
        assert "wink" in self.sanitizer.sanitize_response("Just kidding ;)")

    def test_sanitize_response_normalizes_punctuation(self):
        """Test that multiple punctuation marks are normalized."""
        assert self.sanitizer.sanitize_response("Wow!!!") == "Wow!"
        assert self.sanitizer.sanitize_response("Really???") == "Really?"

    def test_sanitize_response_adds_final_punctuation(self):
        """Test that final punctuation is added if missing."""
        assert self.sanitizer.sanitize_response("Hello there") == "Hello there."
        assert self.sanitizer.sanitize_response("How are you") == "How are you."
        # Should not add if already present
        assert self.sanitizer.sanitize_response("Hello there.") == "Hello there."
        assert self.sanitizer.sanitize_response("How are you?") == "How are you?"

    def test_sanitize_response_filters_banned_words(self):
        """Test that banned words are filtered from responses."""
        assert "badword" not in self.sanitizer.sanitize_response("This contains badword")
        assert "inappropriate" not in self.sanitizer.sanitize_response("This is inappropriate")

    def test_sanitize_response_empty_input(self):
        """Test handling of empty or None input."""
        assert self.sanitizer.sanitize_response("") == ""
        assert self.sanitizer.sanitize_response(None) == ""

    def test_sanitize_input(self):
        """Test that input messages are sanitized properly."""
        # Remove excessive whitespace
        assert self.sanitizer.sanitize_input("Hello   world  ") == "Hello world"
        
        # Filter banned words
        assert "[filtered]" in self.sanitizer.sanitize_input("Hello badword world")
