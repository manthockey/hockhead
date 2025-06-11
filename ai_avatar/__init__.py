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

# Always import MessageSanitizer directly as it's needed for tests and has no heavy dependencies
from ai_avatar.sanitizer import MessageSanitizer

# Define default public API
__all__ = [
    "MessageSanitizer",
    "__version__",
]

# Conditionally import other components
try:
    from ai_avatar.twitch_client import TwitchChatClient
    __all__.append("TwitchChatClient")
except ImportError:
    pass

try:
    from ai_avatar.llm_client import GeminiLLMClient
    __all__.append("GeminiLLMClient")
except ImportError:
    pass

try:
    from ai_avatar.tts_client import ElevenLabsTTSClient
    __all__.append("ElevenLabsTTSClient")
except ImportError:
    pass

try:
    from ai_avatar.memory import MemoryManager
    __all__.append("MemoryManager")
except ImportError:
    pass

try:
    from ai_avatar.unreal_connector import UnrealConnector
    __all__.append("UnrealConnector")
except ImportError:
    pass

try:
    from ai_avatar.orchestrator import Orchestrator
    __all__.append("Orchestrator")
except ImportError:
    pass
