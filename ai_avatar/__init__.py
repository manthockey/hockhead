"""
AI-Powered MetaHuman Avatar System

A system that connects Twitch chat to an AI-powered MetaHuman avatar in Unreal Engine.
The avatar responds to chat messages using a large language model and speaks using
text-to-speech, with synchronized lip movements.

Components:
- Twitch chat connection
- LLM integration (Gemini)
- Text-to-speech (ElevenLabs)
- Memory management
- Unreal Engine integration
"""

__version__ = "0.1.0"

# Import and expose key classes
from ai_avatar.twitch_client import TwitchChatClient
from ai_avatar.llm_client import GeminiLLMClient
from ai_avatar.tts_client import ElevenLabsTTSClient
from ai_avatar.memory import MemoryManager
from ai_avatar.unreal_connector import UnrealConnector
from ai_avatar.orchestrator import Orchestrator

# Define public API
__all__ = [
    "TwitchChatClient",
    "GeminiLLMClient",
    "ElevenLabsTTSClient",
    "MemoryManager",
    "UnrealConnector",
    "Orchestrator",
]
