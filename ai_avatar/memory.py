"""
Memory Management module for AI-Powered MetaHuman Avatar System.

This module provides persistent storage for chat history and user information,
allowing the avatar to remember past interactions and user-specific facts.
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages persistent storage of chat history and user information.
    
    This class handles database operations for storing and retrieving
    conversation history and user-specific facts, enabling the avatar
    to maintain context across sessions.
    """

    def __init__(self, db_path: str, extract_user_facts: bool = True, max_user_facts: int = 10):
        """
        Initialize the memory manager with a SQLite database.
        
        Args:
            db_path: Path to the SQLite database file
            extract_user_facts: Whether to automatically extract facts from conversations
            max_user_facts: Maximum number of facts to store per user
        """
        self.db_path = db_path
        self.extract_user_facts = extract_user_facts
        self.max_user_facts = max_user_facts
        self.lock = threading.RLock()  # Reentrant lock for thread safety
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        logger.info(f"Initialized MemoryManager with database at {db_path}")

    def _init_db(self):
        """Initialize the SQLite database with required tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create chat history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    username TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT,
                    is_question INTEGER DEFAULT 0
                )
            """)
            
            # Create user profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    username TEXT PRIMARY KEY,
                    facts TEXT NOT NULL,  -- JSON string of facts
                    last_seen TEXT NOT NULL,
                    interaction_count INTEGER DEFAULT 1
                )
            """)
            
            # Create index on username for faster lookups
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_username ON chat_history (username)")
            
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a connection to the SQLite database.
        
        Returns:
            sqlite3.Connection: A connection to the database
        """
        return sqlite3.connect(self.db_path)

    async def add_chat_history(
        self, username: str, message: str, response: Optional[str] = None, is_question: bool = False
    ):
        """
        Add a chat message and optional response to history.
        
        Args:
            username: The username of the message sender
            message: The chat message content
            response: The avatar's response (if any)
            is_question: Whether the message is a question
        """
        timestamp = datetime.now().isoformat()
        
        # Run database operation in thread pool to avoid blocking
        await asyncio.to_thread(
            self._add_chat_history_sync,
            username,
            message,
            response,
            is_question,
            timestamp
        )
        
        # If fact extraction is enabled, try to extract facts
        if self.extract_user_facts and message:
            facts = self._extract_user_facts(username, message, response)
            if facts:
                await self.update_user_profile(username, facts)

    def _add_chat_history_sync(
        self, username: str, message: str, response: Optional[str], is_question: bool, timestamp: str
    ):
        """
        Synchronously add chat history to the database (for thread pool execution).
        
        Args:
            username: The username of the message sender
            message: The chat message content
            response: The avatar's response (if any)
            is_question: Whether the message is a question
            timestamp: ISO format timestamp
        """
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO chat_history 
                    (timestamp, username, message, response, is_question)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (timestamp, username, message, response, 1 if is_question else 0)
                )
                conn.commit()

    async def get_recent_history(self, limit: int = 5) -> List[Dict[str, str]]:
        """
        Get recent chat history formatted for LLM context.
        
        Args:
            limit: Maximum number of recent exchanges to retrieve
            
        Returns:
            List of dictionaries with role and content keys
        """
        # Run database operation in thread pool
        rows = await asyncio.to_thread(self._get_recent_history_sync, limit)
        
        # Format for LLM context (compatible with OpenAI-style format)
        history = []
        for row in rows:
            # Add user message
            history.append({
                "role": "user",
                "content": f"{row[1]}: {row[2]}"  # username: message
            })
            
            # Add response if available
            if row[3]:  # response
                history.append({
                    "role": "assistant",
                    "content": row[3]
                })
                
        return history

    def _get_recent_history_sync(self, limit: int) -> List[Tuple]:
        """
        Synchronously get recent chat history from the database.
        
        Args:
            limit: Maximum number of recent exchanges to retrieve
            
        Returns:
            List of tuples containing (id, username, message, response)
        """
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, username, message, response
                    FROM chat_history
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
                # Return in chronological order (oldest first)
                return list(reversed(cursor.fetchall()))

    async def get_user_profile(self, username: str) -> Dict[str, str]:
        """
        Get user profile information.
        
        Args:
            username: The username to retrieve profile for
            
        Returns:
            Dictionary of user facts
        """
        # Run database operation in thread pool
        return await asyncio.to_thread(self._get_user_profile_sync, username)

    def _get_user_profile_sync(self, username: str) -> Dict[str, str]:
        """
        Synchronously get user profile from the database.
        
        Args:
            username: The username to retrieve profile for
            
        Returns:
            Dictionary of user facts
        """
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT facts FROM user_profiles WHERE username = ?",
                    (username,)
                )
                result = cursor.fetchone()
                
                if result:
                    try:
                        return json.loads(result[0])
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode facts JSON for user {username}")
                
                return {}

    async def update_user_profile(self, username: str, facts: Dict[str, str]):
        """
        Update a user's profile with new facts.
        
        Args:
            username: The username to update profile for
            facts: Dictionary of facts to add/update
        """
        # Run database operation in thread pool
        await asyncio.to_thread(self._update_user_profile_sync, username, facts)

    def _update_user_profile_sync(self, username: str, facts: Dict[str, str]):
        """
        Synchronously update user profile in the database.
        
        Args:
            username: The username to update profile for
            facts: Dictionary of facts to add/update
        """
        if not facts:
            return
            
        timestamp = datetime.now().isoformat()
        
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get existing profile
                cursor.execute(
                    "SELECT facts, interaction_count FROM user_profiles WHERE username = ?",
                    (username,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Update existing profile
                    existing_facts = json.loads(result[0])
                    interaction_count = result[1] + 1
                    
                    # Merge new facts with existing ones
                    existing_facts.update(facts)
                    
                    # Limit the number of facts if needed
                    if len(existing_facts) > self.max_user_facts:
                        # Keep only the newest facts (assuming the input facts are newer)
                        # This is a simple approach; a more sophisticated one would track fact ages
                        excess = len(existing_facts) - self.max_user_facts
                        for key in list(existing_facts.keys())[:excess]:
                            if key not in facts:  # Don't remove the facts we just added
                                del existing_facts[key]
                    
                    cursor.execute(
                        """
                        UPDATE user_profiles
                        SET facts = ?, last_seen = ?, interaction_count = ?
                        WHERE username = ?
                        """,
                        (json.dumps(existing_facts), timestamp, interaction_count, username)
                    )
                else:
                    # Create new profile
                    cursor.execute(
                        """
                        INSERT INTO user_profiles
                        (username, facts, last_seen, interaction_count)
                        VALUES (?, ?, ?, 1)
                        """,
                        (username, json.dumps(facts), timestamp)
                    )
                
                conn.commit()

    def _extract_user_facts(
        self, username: str, message: str, response: Optional[str]
    ) -> Dict[str, str]:
        """
        Extract potential facts about a user from their message.
        
        This is a simple implementation that looks for common patterns
        like "I am X" or "My Y is Z". A more sophisticated approach
        could use NLP or the LLM itself for extraction.
        
        Args:
            username: The username of the message sender
            message: The chat message content
            response: The avatar's response (if any)
            
        Returns:
            Dictionary of extracted facts
        """
        facts = {}
        
        # Simple pattern matching for common fact patterns
        # "I am a doctor" -> {"occupation": "doctor"}
        i_am_match = re.search(r"I am (?:a|an) ([a-zA-Z\s]+)", message, re.IGNORECASE)
        if i_am_match:
            facts["occupation"] = i_am_match.group(1).strip()
        
        # "My name is Alice" -> {"name": "Alice"}
        my_name_match = re.search(r"My name is ([a-zA-Z\s]+)", message, re.IGNORECASE)
        if my_name_match:
            facts["name"] = my_name_match.group(1).strip()
        
        # "I live in Paris" -> {"location": "Paris"}
        location_match = re.search(r"I live in ([a-zA-Z\s,]+)", message, re.IGNORECASE)
        if location_match:
            facts["location"] = location_match.group(1).strip()
        
        # "I like/love/enjoy X" -> {"interest": "X"}
        interest_match = re.search(r"I (?:like|love|enjoy) ([a-zA-Z\s]+)", message, re.IGNORECASE)
        if interest_match:
            facts["interest"] = interest_match.group(1).strip()
        
        return facts

    async def save_to_disk(self):
        """
        Ensure all data is saved to disk.
        
        This is mostly a no-op for SQLite as it handles persistence,
        but it's included for API completeness and potential future use.
        """
        # SQLite handles this automatically with commits
        # This method exists for API completeness
        pass

    async def close(self):
        """Close any open resources."""
        # No persistent connections to close in current implementation
        pass

    async def is_moderator(self, username: str) -> bool:
        """
        Check if a user is a moderator (placeholder implementation).
        
        In a real implementation, this would check Twitch badges or a config list.
        
        Args:
            username: The username to check
            
        Returns:
            True if the user is a moderator, False otherwise
        """
        # Placeholder implementation - in reality, would check Twitch badges
        # or a configured list of moderators
        return False
