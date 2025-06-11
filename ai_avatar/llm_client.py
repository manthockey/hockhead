"""
LLM Client module for AI-Powered MetaHuman Avatar System.

This module provides a client for Google's Generative AI (Gemini) API,
formatting prompts and handling responses for the avatar's conversation.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class GeminiLLMClient:
    """
    Client for Google's Generative AI (Gemini) API.
    
    This client handles authentication, prompt formatting, and response generation
    using the Gemini model.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-1.5-flash-latest",
        temperature: float = 0.7,
        max_tokens: int = 200,
        system_prompt: str = "",
    ):
        """
        Initialize the Gemini LLM client.
        
        Args:
            api_key: API key for authentication with Google Generative AI
            model_name: Name of the Gemini model to use
            temperature: Controls randomness in responses (0.0-1.0)
            max_tokens: Maximum number of tokens in the response
            system_prompt: System instructions for the model
        """
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.model = None
        
        # Lazy import Google Generative AI
        try:
            import google.generativeai as genai
            from google.generativeai.types import GenerationConfig
            
            # Configure the Gemini API
            genai.configure(api_key=self.api_key)
            
            # Initialize model
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                ),
            )
            
            logger.info(f"Initialized Gemini LLM client with model: {model_name}")
        except ImportError:
            logger.warning("Google Generative AI package not found. LLM functionality will be disabled.")
            self.model = None

    async def generate_response(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]] = None,
        user_profile: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Generate a response from the LLM based on user message and context.
        
        Args:
            user_message: The user's message to respond to
            chat_history: List of previous messages in the conversation
            user_profile: Optional dictionary of user information for context
            
        Returns:
            str: The generated response text, or None if generation failed
        """
        # Early return if model is not available
        if self.model is None:
            logger.warning("Cannot generate response: Gemini model not initialized")
            return None
            
        try:
            # Create a new chat session
            chat = self.model.start_chat(history=[])
            
            # Add system prompt if provided
            prompt = self._build_prompt(user_message, chat_history, user_profile)
            
            # Run in executor to avoid blocking
            response = await asyncio.to_thread(
                self._generate_response_sync, chat, prompt
            )
            
            if response:
                return response.text
            return None
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return None

    def _generate_response_sync(self, chat, prompt):
        """
        Generate a response synchronously (to be run in a thread pool).
        
        Args:
            chat: The Gemini chat session
            prompt: The formatted prompt
            
        Returns:
            The response from the model
        """
        return chat.send_message(prompt)

    def _build_prompt(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]] = None,
        user_profile: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Build a prompt for the LLM including context and history.
        
        Args:
            user_message: The user's message to respond to
            chat_history: List of previous messages in the conversation
            user_profile: Optional dictionary of user information for context
            
        Returns:
            str: The formatted prompt
        """
        prompt_parts = []
        
        # Add system prompt
        if self.system_prompt:
            prompt_parts.append(self.system_prompt)
        
        # Add user profile context if available
        if user_profile and isinstance(user_profile, dict) and user_profile:
            profile_text = "User information: " + ", ".join(
                f"{key}: {value}" for key, value in user_profile.items()
            )
            prompt_parts.append(profile_text)
        
        # Add chat history for context
        if chat_history and isinstance(chat_history, list) and chat_history:
            history_text = "Recent conversation:\n"
            for entry in chat_history:
                if "role" in entry and "content" in entry:
                    role = "Avatar" if entry["role"] == "assistant" else entry["role"].capitalize()
                    history_text += f"{role}: {entry['content']}\n"
            prompt_parts.append(history_text)
        
        # Add the current user message
        prompt_parts.append(f"User: {user_message}\n\nAvatar:")
        
        # Join all parts with newlines
        return "\n\n".join(prompt_parts)
