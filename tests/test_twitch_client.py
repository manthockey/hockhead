"""
Tests for the TwitchChatClient class.

This module contains unit tests for the TwitchChatClient class,
focusing on IRC message parsing and connection handling.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_avatar.twitch_client import TwitchChatClient


class TestTwitchChatClient:
    """Test suite for the TwitchChatClient class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TwitchChatClient(
            token="test_token",
            username="test_bot",
            channel="test_channel",
            use_ssl=False,
            host="irc.test.twitch.tv",
            port=6667,
            reconnect_delay=0
        )
        # Make sure channel has # prefix for tests
        self.client.channel = "#test_channel"

    @pytest.mark.parametrize("irc_line, expected_username, expected_message", [
        # Standard IRC format
        (
            ":alice!alice@alice.tmi.twitch.tv PRIVMSG #test_channel :Hello world!",
            "alice", 
            "Hello world!"
        ),
        # IRC with tags (display-name present)
        (
            "@badge-info=;badges=;color=#FF0000;display-name=Bob;emotes=;flags= "
            ":bob!bob@bob.tmi.twitch.tv PRIVMSG #test_channel :How are you?",
            "Bob",  # Should use display-name when available
            "How are you?"
        ),
        # IRC with tags (display-name empty)
        (
            "@badge-info=;badges=;color=#FF0000;display-name=;emotes=;flags= "
            ":carol!carol@carol.tmi.twitch.tv PRIVMSG #test_channel :Testing!",
            "carol",  # Should fall back to username when display-name is empty
            "Testing!"
        ),
        # Message with special characters
        (
            ":dave!dave@dave.tmi.twitch.tv PRIVMSG #test_channel :Hello! How's it going? 😊",
            "dave",
            "Hello! How's it going? 😊"
        ),
        # Message with bot mention
        (
            ":eve!eve@eve.tmi.twitch.tv PRIVMSG #test_channel :Hey @test_bot can you help?",
            "eve",
            "Hey @test_bot can you help?"
        ),
        # Message with Twitch emotes
        (
            ":frank!frank@frank.tmi.twitch.tv PRIVMSG #test_channel :That's funny Kappa",
            "frank",
            "That's funny Kappa"
        ),
    ])
    def test_parse_message(self, irc_line, expected_username, expected_message):
        """Test parsing of different IRC message formats."""
        username, message = self.client._parse_message(irc_line)
        
        assert username == expected_username
        assert message == expected_message

    def test_parse_message_malformed(self):
        """Test parsing of malformed messages."""
        # Completely invalid format
        username, message = self.client._parse_message("This is not an IRC message")
        assert username is None
        assert message is None
        
        # Missing parts
        username, message = self.client._parse_message("PRIVMSG #test_channel :Incomplete message")
        assert username is None
        assert message is None

    @pytest.mark.asyncio
    async def test_on_message_callback(self):
        """Test that the on_message callback is triggered with correct parameters."""
        # Set up a mock callback
        mock_callback = AsyncMock()
        self.client.on_message = mock_callback
        
        # Create a reader that returns a valid IRC message
        self.client.reader = MagicMock()
        self.client.reader.read.side_effect = [
            b":alice!alice@alice.tmi.twitch.tv PRIVMSG #test_channel :Hello world!\r\n",
            b"",  # Empty response to trigger disconnect
        ]
        
        # Run the listen method with a timeout
        with pytest.raises(asyncio.CancelledError):
            # Start listening and cancel after a short time
            listen_task = asyncio.create_task(self.client._listen_for_messages())
            await asyncio.sleep(0.1)
            listen_task.cancel()
            await listen_task
        
        # Check if callback was called with correct parameters
        mock_callback.assert_called_once_with("alice", "Hello world!")

    @pytest.mark.asyncio
    async def test_ping_pong(self):
        """Test that PING messages are responded to with PONG."""
        # Set up a mock writer
        self.client.writer = MagicMock()
        
        # Create a reader that returns a PING message
        self.client.reader = MagicMock()
        self.client.reader.read.side_effect = [
            b"PING :tmi.twitch.tv\r\n",
            b"",  # Empty response to trigger disconnect
        ]
        
        # Run the listen method with a timeout
        with pytest.raises(asyncio.CancelledError):
            # Start listening and cancel after a short time
            listen_task = asyncio.create_task(self.client._listen_for_messages())
            await asyncio.sleep(0.1)
            listen_task.cancel()
            await listen_task
        
        # Check if PONG was sent
        self.client.writer.write.assert_called_with(b"PONG :tmi.twitch.tv\r\n")
