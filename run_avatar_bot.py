#!/usr/bin/env python3
"""
AI-Powered MetaHuman Avatar System - Main Entry Point

This script initializes and runs the AI Avatar system, connecting Twitch chat
to an AI-powered MetaHuman avatar in Unreal Engine. It handles configuration loading,
component initialization, and graceful shutdown.

Usage:
    python run_avatar_bot.py [--config CONFIG_FILE] [--log-level {DEBUG,INFO,WARNING,ERROR}]
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from ai_avatar.config import Config, load_config
from ai_avatar.orchestrator import Orchestrator


def setup_logging(log_level: str):
    """
    Configure logging for the application.
    
    Args:
        log_level: The logging level to use (DEBUG, INFO, WARNING, ERROR)
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
        
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # Log to console
            logging.FileHandler(logs_dir / "avatar_bot.log")  # Log to file
        ]
    )
    
    # Set specific loggers to different levels if needed
    # For example, to reduce verbosity of some libraries:
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def validate_config(config: Config) -> bool:
    """
    Validate that the configuration has all required values.
    
    Args:
        config: The loaded configuration object
        
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    # Check Twitch configuration
    if not config.twitch.oauth_token:
        logger.error("Missing Twitch OAuth token. Set TWITCH_OAUTH_TOKEN environment variable.")
        return False
        
    if not config.twitch.username:
        logger.error("Missing Twitch username. Set TWITCH_USERNAME environment variable.")
        return False
        
    if not config.twitch.channel:
        logger.error("Missing Twitch channel. Set TWITCH_CHANNEL environment variable.")
        return False
    
    # Check LLM configuration (Gemini API key is provided in default config)
    if not config.llm.api_key:
        logger.error("Missing LLM API key. Set GEMINI_API_KEY environment variable.")
        return False
    
    # Check TTS configuration
    if not config.tts.api_key:
        logger.warning("Missing ElevenLabs API key. TTS will not work. Set ELEVENLABS_API_KEY environment variable.")
        
    if not config.tts.voice_id:
        logger.warning("Missing ElevenLabs voice ID. TTS will not work. Set ELEVENLABS_VOICE_ID environment variable.")
    
    return True


async def run_avatar_bot(config: Config):
    """
    Initialize and run the AI Avatar system.
    
    Args:
        config: The loaded and validated configuration
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting AI Avatar Bot")
    
    # Create the orchestrator
    orchestrator = Orchestrator(config)
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    
    # Use try/except for signal handlers since they're not supported on Windows
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(shutdown(orchestrator, loop))
            )
        logger.debug("Signal handlers registered for graceful shutdown")
    except NotImplementedError:
        # Windows doesn't support add_signal_handler
        logger.info("Signal handlers not available on this platform (Windows). Use Ctrl+C to stop.")
        # No alternative signal handling on Windows - we'll rely on KeyboardInterrupt exception
    
    # Test components before starting
    logger.info("Testing components...")
    test_results = await orchestrator.test_components()
    
    for component, status in test_results.items():
        if status:
            logger.info(f"✓ {component} connection test passed")
        else:
            logger.warning(f"✗ {component} connection test failed")
    
    # Start the orchestrator
    logger.info("Starting orchestrator...")
    tasks = await orchestrator.start()
    
    # Keep running until shutdown
    try:
        logger.info("AI Avatar Bot is running. Press Ctrl+C to stop.")
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass


async def shutdown(orchestrator: Orchestrator, loop: asyncio.AbstractEventLoop):
    """
    Perform graceful shutdown of the system.
    
    Args:
        orchestrator: The orchestrator instance to stop
        loop: The event loop to stop
    """
    logger = logging.getLogger(__name__)
    logger.info("Shutting down AI Avatar Bot...")
    
    # Stop the orchestrator
    await orchestrator.stop()
    
    # Stop the event loop
    loop.stop()


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="AI-Powered MetaHuman Avatar System")
    
    parser.add_argument(
        "--config",
        help="Path to configuration file",
        default=None
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config()
        
        # Override log level from arguments
        config.log_level = args.log_level
        
        # Validate configuration
        if not validate_config(config):
            logger.error("Invalid configuration. Exiting.")
            sys.exit(1)
        
        # Run the avatar bot
        asyncio.run(run_avatar_bot(config))
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Exiting.")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
