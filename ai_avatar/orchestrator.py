"""
Orchestrator module for AI-Powered MetaHuman Avatar System.

This module coordinates all components of the system, managing the flow
of data from Twitch chat through the LLM and TTS to the Unreal Engine avatar.
"""

import asyncio
import logging
import queue
import time
from typing import Dict, List, Optional, Set, Tuple, Union

from ai_avatar.twitch_client import TwitchChatClient
from ai_avatar.llm_client import GeminiLLMClient
from ai_avatar.tts_client import ElevenLabsTTSClient
from ai_avatar.memory import MemoryManager
from ai_avatar.unreal_connector import UnrealConnector
from ai_avatar.sanitizer import MessageSanitizer
from ai_avatar.config import Config

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Central coordinator for the AI Avatar system.
    
    This class manages the flow of data between all components:
    - Receiving and filtering Twitch chat messages
    - Processing messages through the LLM
    - Converting responses to speech with TTS
    - Sending audio to Unreal Engine
    - Maintaining conversation context in memory
    """

    def __init__(self, config: Config):
        """
        Initialize the orchestrator with all components.
        
        Args:
            config: Configuration object containing settings for all components
        """
        self.config = config
        
        # Initialize components
        self.twitch_client = TwitchChatClient(
            token=config.twitch.oauth_token,
            username=config.twitch.username,
            channel=config.twitch.channel
        )
        
        self.llm_client = GeminiLLMClient(
            api_key=config.llm.api_key,
            model_name=config.llm.model_name,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            system_prompt=config.llm.system_prompt
        )
        
        self.tts_client = ElevenLabsTTSClient(
            api_key=config.tts.api_key,
            voice_id=config.tts.voice_id,
            model_id=config.tts.model_id,
            stability=config.tts.stability,
            similarity_boost=config.tts.similarity_boost,
            output_format=config.tts.output_format
        )
        
        self.memory_manager = MemoryManager(
            db_path=config.memory.db_path,
            extract_user_facts=config.memory.extract_user_facts,
            max_user_facts=config.memory.max_user_facts
        )
        
        self.unreal_connector = UnrealConnector(
            host=config.unreal.host,
            port=config.unreal.port,
            audio_output_path=config.unreal.audio_output_path,
            use_alternating_files=config.unreal.use_alternating_files
        )
        
        self.sanitizer = MessageSanitizer(
            bot_name=config.twitch.username,
            respond_to_prefix=config.twitch.respond_to_prefix,
            respond_to_questions=config.twitch.respond_to_questions,
            banned_words=config.banned_words,
            max_response_chars=config.max_response_chars
        )
        
        # Message queue and processing state
        self.message_queue = asyncio.Queue(maxsize=config.twitch.max_queue_size)
        self.running = False
        self.processing_task = None
        
        # User cooldowns (if enabled)
        self.user_cooldowns = {}
        self.cooldown_seconds = config.twitch.cooldown_seconds
        
        # Set up Twitch client callbacks
        self.twitch_client.on_message = self._on_twitch_message
        
        logger.info("Orchestrator initialized with all components")

    async def start(self):
        """Start the orchestrator and all components."""
        if self.running:
            logger.warning("Orchestrator is already running")
            return
            
        self.running = True
        
        # Start Twitch client
        logger.info("Starting Twitch client...")
        twitch_task = asyncio.create_task(self.twitch_client.connect_and_listen())
        
        # Start message processing
        logger.info("Starting message processor...")
        self.processing_task = asyncio.create_task(self._process_messages())
        
        # Return tasks for the caller to await if desired
        return twitch_task, self.processing_task

    async def stop(self):
        """Stop the orchestrator and all components."""
        if not self.running:
            logger.warning("Orchestrator is not running")
            return
            
        self.running = False
        
        # Stop Twitch client
        await self.twitch_client.disconnect()
        
        # Cancel processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
            
        # Save memory to disk
        await self.memory_manager.save_to_disk()
        
        # Clean up resources
        await self.memory_manager.close()
        
        logger.info("Orchestrator stopped")

    async def _on_twitch_message(self, username: str, message: str):
        """
        Handle incoming Twitch chat messages.
        
        Args:
            username: The username of the message sender
            message: The chat message content
        """
        logger.debug(f"Received message from {username}: {message}")
        
        # Check if we should respond to this message
        if not self.sanitizer.should_respond_to(message, username, self.config.twitch.username):
            logger.debug(f"Ignoring message from {username}")
            return
            
        # Check cooldown if enabled
        if self.cooldown_seconds > 0:
            current_time = time.time()
            if username in self.user_cooldowns:
                last_time = self.user_cooldowns[username]
                if current_time - last_time < self.cooldown_seconds:
                    logger.debug(f"User {username} is on cooldown, ignoring message")
                    return
            
            # Update cooldown timestamp
            self.user_cooldowns[username] = current_time
        
        # Sanitize message
        sanitized_message = self.sanitizer.sanitize_input(message)
        
        # Check if queue is full
        try:
            # Create request object
            request = {
                "username": username,
                "message": sanitized_message,
                "raw_message": message,
                "timestamp": time.time(),
                "is_question": self.sanitizer.is_question(message)
            }
            
            # Add to queue with timeout to avoid blocking
            await asyncio.wait_for(
                self.message_queue.put(request),
                timeout=1.0
            )
            logger.info(f"Queued message from {username} for processing")
            
        except asyncio.QueueFull:
            logger.warning("Message queue full, dropping message from {username}")
        except asyncio.TimeoutError:
            logger.warning("Timeout adding message to queue")

    async def _process_messages(self):
        """
        Main processing loop for messages in the queue.
        
        This method runs as a task, continuously pulling messages from the queue
        and processing them through the LLM->TTS->Unreal pipeline.
        """
        logger.info("Message processor started")
        
        while self.running:
            try:
                # Get next message from queue
                request = await self.message_queue.get()
                
                username = request["username"]
                message = request["message"]
                is_question = request["is_question"]
                
                logger.info(f"Processing message from {username}: {message}")
                
                # Process the message through the pipeline
                await self._process_single_message(username, message, is_question)
                
                # Mark task as done
                self.message_queue.task_done()
                
            except asyncio.CancelledError:
                # Task was cancelled, exit loop
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
        
        logger.info("Message processor stopped")

    async def _process_single_message(self, username: str, message: str, is_question: bool):
        """
        Process a single message through the complete pipeline.
        
        Args:
            username: The username of the message sender
            message: The sanitized message content
            is_question: Whether the message is a question
        """
        try:
            # Log the message to memory
            await self.memory_manager.add_chat_history(
                username=username,
                message=message,
                is_question=is_question
            )
            
            # Get recent chat history for context
            recent_history = await self.memory_manager.get_recent_history(
                limit=self.config.llm.history_length
            )
            
            # Get user profile for personalization
            user_profile = await self.memory_manager.get_user_profile(username)
            
            # Generate response with LLM
            logger.debug(f"Sending message to LLM: {message}")
            response_text = await self.llm_client.generate_response(
                user_message=message,
                chat_history=recent_history,
                user_profile=user_profile
            )
            
            if not response_text:
                logger.warning(f"LLM returned empty response for message from {username}")
                return
                
            # Sanitize response for TTS
            sanitized_response = self.sanitizer.sanitize_response(response_text)
            
            if not sanitized_response:
                logger.warning("Sanitized response is empty, skipping TTS")
                return
                
            # Update memory with the response
            await self.memory_manager.add_chat_history(
                username=username,
                message=message,
                response=sanitized_response,
                is_question=is_question
            )
            
            # Generate speech with TTS
            logger.debug(f"Sending response to TTS: {sanitized_response}")
            audio_data = await self.tts_client.synthesize(sanitized_response)
            
            if not audio_data:
                logger.warning("TTS returned no audio data")
                return
                
            # Send audio to Unreal Engine
            logger.debug("Sending audio to Unreal Engine")
            file_path = await self.unreal_connector.send_audio(
                audio_data=audio_data,
                file_extension=self.config.tts.output_format
            )
            
            if file_path:
                logger.info(f"Successfully processed message from {username}")
            else:
                logger.warning(f"Failed to send audio to Unreal Engine for message from {username}")
                
            # Clean up old files periodically
            await self.unreal_connector.cleanup_old_files()
            
        except Exception as e:
            logger.error(f"Error in message processing pipeline: {str(e)}", exc_info=True)

    async def test_components(self) -> Dict[str, bool]:
        """
        Test all components to verify they're working correctly.
        
        Returns:
            Dict[str, bool]: Status of each component test
        """
        results = {}
        
        # Test Unreal connection
        try:
            results["unreal"] = await self.unreal_connector.test_connection()
        except Exception as e:
            logger.error(f"Unreal connection test failed: {str(e)}")
            results["unreal"] = False
            
        # Other component tests could be added here
        
        return results
