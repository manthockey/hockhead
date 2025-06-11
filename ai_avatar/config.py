"""
Configuration module for AI-Powered MetaHuman Avatar System.

This module defines the configuration schema using Pydantic models and provides
functionality to load configuration from environment variables and/or a config file.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Load environment variables from .env file if it exists
load_dotenv()


class TwitchConfig(BaseModel):
    """Configuration for Twitch chat connection."""

    oauth_token: str = Field(
        default_factory=lambda: os.getenv("TWITCH_OAUTH_TOKEN", "")
    )
    username: str = Field(default_factory=lambda: os.getenv("TWITCH_USERNAME", ""))
    channel: str = Field(default_factory=lambda: os.getenv("TWITCH_CHANNEL", ""))
    respond_to_prefix: bool = True
    respond_to_questions: bool = True
    cooldown_seconds: int = 0  # 0 means no cooldown
    max_queue_size: int = 5


class LLMConfig(BaseModel):
    """Configuration for the Language Model (Gemini)."""

    provider_type: str = "gemini"
    model_name: str = "gemini-1.5-flash-latest"
    api_key: str = Field(
        default_factory=lambda: os.getenv(
            "GEMINI_API_KEY", "AIzaSyC1CgTurH_IOd4TrnzPIVpmWn3f7Rh37Cw"
        )
    )
    temperature: float = 0.7
    max_tokens: int = 200
    system_prompt: str = (
        "You are a friendly AI avatar streaming on Twitch. "
        "Keep your responses concise, engaging, and appropriate for all audiences. "
        "You speak in a conversational tone and can express emotions through your words."
    )
    history_length: int = 5  # Number of recent exchanges to include in context


class TTSConfig(BaseModel):
    """Configuration for ElevenLabs Text-to-Speech."""

    api_key: str = Field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", ""))
    voice_id: str = Field(default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", ""))
    model_id: str = "eleven_monolingual_v1"
    stability: float = 0.5
    similarity_boost: float = 0.5
    output_format: str = "mp3"  # mp3 or pcm


class UnrealConfig(BaseModel):
    """Configuration for Unreal Engine integration."""

    host: str = "127.0.0.1"
    port: int = 5555
    audio_output_path: str = Field(
        default_factory=lambda: os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "audio_output"
        )
    )
    use_alternating_files: bool = True  # Use two files to avoid conflicts


class MemoryConfig(BaseModel):
    """Configuration for memory management."""

    db_path: str = Field(
        default_factory=lambda: os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "memory.db"
        )
    )
    extract_user_facts: bool = True
    max_user_facts: int = 10  # Max facts to store per user
    summarize_history: bool = False  # Whether to periodically summarize old history


class Config(BaseModel):
    """Main configuration for the AI Avatar system."""

    twitch: TwitchConfig = Field(default_factory=TwitchConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    unreal: UnrealConfig = Field(default_factory=UnrealConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    log_level: str = "INFO"
    banned_words: List[str] = Field(default_factory=list)
    max_response_chars: int = 500

    @field_validator("unreal")
    def ensure_audio_directory_exists(cls, v):
        """Ensure the audio output directory exists."""
        os.makedirs(v.audio_output_path, exist_ok=True)
        return v


def load_config() -> Config:
    """
    Load configuration from environment variables and return a Config object.
    
    Returns:
        Config: The loaded configuration
    """
    return Config()
