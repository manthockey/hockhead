"""
Message Sanitizer module for AI-Powered MetaHuman Avatar System.

This module provides utilities for filtering incoming messages,
determining which messages should receive a response, and sanitizing
text for LLM prompts and TTS output.
"""

import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class MessageSanitizer:
    """
    Handles message filtering and text sanitization.
    
    This class determines which messages should receive a response,
    filters out inappropriate content, and formats text for TTS.
    """

    def __init__(
        self,
        bot_name: str,
        respond_to_prefix: bool = True,
        respond_to_questions: bool = True,
        banned_words: List[str] = None,
        max_response_chars: int = 500,
    ):
        """
        Initialize the message sanitizer.
        
        Args:
            bot_name: The name of the bot/avatar
            respond_to_prefix: Whether to respond to messages prefixed with the bot's name
            respond_to_questions: Whether to respond to questions (messages with '?')
            banned_words: List of words to filter out
            max_response_chars: Maximum length for responses
        """
        self.bot_name = bot_name.lower()
        self.respond_to_prefix = respond_to_prefix
        self.respond_to_questions = respond_to_questions
        self.banned_words = [word.lower() for word in (banned_words or [])]
        self.max_response_chars = max_response_chars
        
        # Common Twitch emotes to handle in TTS
        self.twitch_emotes = {
            "Kappa": "kappa emote",
            "PogChamp": "pog champ emote",
            "LUL": "laughing emote",
            # Add more common emotes as needed
        }
        
        logger.info(f"Initialized MessageSanitizer with bot name: {bot_name}")

    def should_respond_to(self, message: str, username: str, bot_username: str) -> bool:
        """
        Determine if a message should receive a response.
        
        Args:
            message: The chat message
            username: The sender's username
            bot_username: The bot's Twitch username
            
        Returns:
            bool: True if the message should get a response, False otherwise
        """
        # Ignore bot's own messages
        if username.lower() == bot_username.lower():
            return False
            
        # Check if message contains banned words
        if self._contains_banned_words(message):
            logger.debug(f"Message from {username} contains banned words, ignoring")
            return False
            
        message_lower = message.lower()
        
        # Check for direct mentions of the bot
        if self.respond_to_prefix:
            # Check for common ways to address the bot
            prefixes = [
                f"{self.bot_name}:",
                f"@{self.bot_name}",
                f"!{self.bot_name}",
                f"hey {self.bot_name}",
                f"hi {self.bot_name}",
            ]
            
            for prefix in prefixes:
                if message_lower.startswith(prefix):
                    return True
            
            # Check if bot name is mentioned anywhere in the message
            if self.bot_name in message_lower.split():
                return True
                
        # Check if it's a question
        if self.respond_to_questions and "?" in message:
            return True
            
        # Additional custom logic can be added here
        
        return False

    def sanitize_input(self, message: str) -> str:
        """
        Sanitize input message for LLM prompt.
        
        Args:
            message: The raw chat message
            
        Returns:
            str: Sanitized message
        """
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', message).strip()
        
        # Filter banned words if any
        if self.banned_words:
            for word in self.banned_words:
                sanitized = re.sub(
                    r'\b' + re.escape(word) + r'\b', 
                    '[filtered]', 
                    sanitized, 
                    flags=re.IGNORECASE
                )
                
        return sanitized

    def sanitize_response(self, text: str) -> str:
        """
        Sanitize LLM response for TTS.
        
        Args:
            text: The LLM-generated response
            
        Returns:
            str: Sanitized response ready for TTS
        """
        if not text:
            return ""
            
        # Remove any role prefixes that might have been generated
        # (e.g., "Assistant:" or "Bot:")
        text = re.sub(r'^(Assistant|Bot|Avatar):\s*', '', text, flags=re.IGNORECASE)
        
        # Trim if too long
        if len(text) > self.max_response_chars:
            # Try to cut at a sentence boundary
            sentences = re.split(r'(?<=[.!?])\s+', text[:self.max_response_chars + 50])
            if len(sentences) > 1:
                # Remove the last (potentially incomplete) sentence
                text = ' '.join(sentences[:-1])
            else:
                # Just truncate if we can't find sentence boundaries
                text = text[:self.max_response_chars] + "..."
        
        # Handle common Twitch emotes for better TTS
        for emote, replacement in self.twitch_emotes.items():
            text = re.sub(r'\b' + re.escape(emote) + r'\b', replacement, text)
        
        # Handle emoticons
        text = re.sub(r':\)', ' smiling ', text)
        text = re.sub(r':\(', ' sad face ', text)
        text = re.sub(r':D', ' big smile ', text)
        text = re.sub(r';-?\)', ' wink ', text)
        
        # Replace multiple exclamation marks/question marks with single ones
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'\?{2,}', '?', text)
        
        # Filter banned words again (in case LLM generated them)
        if self.banned_words:
            for word in self.banned_words:
                text = re.sub(
                    r'\b' + re.escape(word) + r'\b', 
                    '', 
                    text, 
                    flags=re.IGNORECASE
                )
        
        # Ensure text ends with punctuation for better TTS prosody
        if text and not re.search(r'[.!?]$', text):
            text = text + '.'
            
        return text.strip()

    def _contains_banned_words(self, text: str) -> bool:
        """
        Check if text contains any banned words.
        
        Args:
            text: Text to check
            
        Returns:
            bool: True if banned words are found, False otherwise
        """
        if not self.banned_words:
            return False
            
        text_lower = text.lower()
        for word in self.banned_words:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                return True
                
        return False

    def is_question(self, message: str) -> bool:
        """
        Determine if a message is a question.
        
        Args:
            message: The chat message
            
        Returns:
            bool: True if the message is likely a question
        """
        # Simple check for question mark
        if "?" in message:
            return True
            
        # Check for common question starters
        question_starters = [
            "who", "what", "when", "where", "why", "how", "is", "are", "can", 
            "could", "would", "will", "should", "do", "does", "did"
        ]
        
        words = message.lower().split()
        if words and words[0] in question_starters:
            return True
            
        return False

    def extract_bot_command(self, message: str) -> Optional[Tuple[str, str]]:
        """
        Extract a bot command from a message if present.
        
        Args:
            message: The chat message
            
        Returns:
            Optional[Tuple[str, str]]: (command, args) or None if no command
        """
        # Check for !command format
        command_match = re.match(r'!(\w+)\s*(.*)', message)
        if command_match:
            command = command_match.group(1).lower()
            args = command_match.group(2).strip()
            return command, args
            
        return None
