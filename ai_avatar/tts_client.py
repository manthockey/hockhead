"""
Text-to-Speech Client module for AI-Powered MetaHuman Avatar System.

This module provides a client for ElevenLabs Text-to-Speech API,
converting text responses into natural-sounding speech audio.
"""

import asyncio
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ElevenLabsTTSClient:
    """
    Client for ElevenLabs Text-to-Speech API.
    
    This class handles authentication, request formatting, and audio retrieval
    from the ElevenLabs TTS service.
    """

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        model_id: str = "eleven_monolingual_v1",
        stability: float = 0.5,
        similarity_boost: float = 0.5,
        output_format: str = "mp3",
    ):
        """
        Initialize the ElevenLabs TTS client.
        
        Args:
            api_key: API key for authentication with ElevenLabs
            voice_id: ID of the voice to use for synthesis
            model_id: ID of the TTS model to use
            stability: Controls stability of the voice (0.0-1.0)
            similarity_boost: Controls similarity to the original voice (0.0-1.0)
            output_format: Audio format to request (mp3 or pcm)
        """
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.output_format = output_format
        self.base_url = "https://api.elevenlabs.io/v1"
        self.tts_enabled = True
        
        # Set up headers
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": f"audio/{self.output_format}"
        }
        
        # Lazy import requests
        try:
            import requests
            self.requests = requests
            logger.info(f"Initialized ElevenLabs TTS client with voice ID: {voice_id}")
        except ImportError:
            logger.warning("Requests package not found. TTS functionality will be disabled.")
            self.requests = None
            self.tts_enabled = False

    async def synthesize(self, text: str) -> Optional[bytes]:
        """
        Synthesize text into speech audio.
        
        Args:
            text: The text to convert to speech
            
        Returns:
            bytes: The audio data, or None if synthesis failed
        """
        # Early return if TTS is disabled
        if not self.tts_enabled or self.requests is None:
            logger.warning("TTS is disabled due to missing dependencies")
            return None
            
        if not text or not text.strip():
            logger.warning("Empty text provided for synthesis, skipping TTS call")
            return None
            
        # Trim text if too long (ElevenLabs has character limits)
        if len(text) > 5000:
            logger.warning(f"Text too long ({len(text)} chars), trimming to 5000 chars")
            text = text[:4997] + "..."
            
        # Prepare request payload
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost
            }
        }
        
        url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        
        try:
            # Run in executor to avoid blocking
            response = await asyncio.to_thread(
                self._synthesize_sync, url, payload
            )
            
            if response and response.status_code == 200:
                logger.info(f"Successfully synthesized {len(text)} chars of text")
                return response.content
            else:
                status = response.status_code if response else "No response"
                error = response.text if response else "Unknown error"
                logger.error(f"TTS API error: {status}, {error}")
                return None
                
        except Exception as e:
            logger.error(f"Error synthesizing speech: {str(e)}")
            return None

    def _synthesize_sync(self, url: str, payload: Dict) -> Optional:
        """
        Make a synchronous request to the TTS API (to be run in a thread pool).
        
        Args:
            url: The API endpoint URL
            payload: The request payload
            
        Returns:
            requests.Response: The API response
        """
        return self.requests.post(
            url,
            json=payload,
            headers=self.headers,
            timeout=30  # Reasonable timeout for TTS generation
        )
