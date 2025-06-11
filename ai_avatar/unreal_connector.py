"""
Unreal Engine Connector module for AI-Powered MetaHuman Avatar System.

This module provides communication between the Python orchestrator and Unreal Engine,
writing audio files and notifying Unreal via UDP when new audio is ready to play.
"""

import asyncio
import logging
import os
import socket
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class UnrealConnector:
    """
    Handles communication with Unreal Engine.
    
    This class manages writing audio files and sending UDP notifications
    to Unreal Engine when new audio is ready to be played.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5555,
        audio_output_path: str = "./audio_output",
        use_alternating_files: bool = True,
    ):
        """
        Initialize the Unreal Engine connector.
        
        Args:
            host: The hostname or IP address of the Unreal Engine application
            port: The UDP port that Unreal Engine is listening on
            audio_output_path: Directory to store audio files
            use_alternating_files: Whether to alternate between two files to avoid conflicts
        """
        self.host = host
        self.port = port
        self.audio_output_path = audio_output_path
        self.use_alternating_files = use_alternating_files
        
        # Create audio output directory if it doesn't exist
        os.makedirs(self.audio_output_path, exist_ok=True)
        
        # For alternating files
        self.current_file_index = 0
        self.file_extensions = ["mp3", "wav"]  # Support both formats
        
        logger.info(f"Initialized UnrealConnector to {host}:{port}")

    async def send_audio(self, audio_data: bytes, file_extension: str = "mp3") -> Optional[str]:
        """
        Save audio data to file and notify Unreal Engine.
        
        Args:
            audio_data: Binary audio data
            file_extension: File extension (mp3 or wav)
            
        Returns:
            str: Path to the saved audio file, or None if failed
        """
        if not audio_data:
            logger.error("No audio data provided")
            return None
            
        # Validate file extension
        if file_extension not in self.file_extensions:
            logger.warning(f"Unsupported file extension: {file_extension}, using mp3")
            file_extension = "mp3"
        
        # Generate filename
        filename = self._get_next_filename(file_extension)
        filepath = os.path.join(self.audio_output_path, filename)
        
        try:
            # Write audio data to file
            await asyncio.to_thread(self._write_file_sync, filepath, audio_data)
            
            # Notify Unreal Engine
            success = await self._send_udp_notification(filename)
            
            if success:
                logger.info(f"Audio file {filename} sent to Unreal Engine")
                return filepath
            else:
                logger.error("Failed to notify Unreal Engine")
                return filepath  # Still return the path even if notification failed
                
        except Exception as e:
            logger.error(f"Error sending audio to Unreal Engine: {str(e)}")
            return None

    def _get_next_filename(self, extension: str) -> str:
        """
        Get the next filename to use, implementing alternating files if enabled.
        
        Args:
            extension: File extension (mp3 or wav)
            
        Returns:
            str: Filename to use
        """
        if self.use_alternating_files:
            # Alternate between two files to avoid conflicts
            filename = f"audio_output_{self.current_file_index}.{extension}"
            self.current_file_index = 1 - self.current_file_index  # Toggle between 0 and 1
        else:
            # Use timestamp for unique filenames
            import time
            timestamp = int(time.time() * 1000)
            filename = f"audio_output_{timestamp}.{extension}"
            
        return filename

    def _write_file_sync(self, filepath: str, data: bytes):
        """
        Synchronously write data to file (for thread pool execution).
        
        Args:
            filepath: Path to the file to write
            data: Binary data to write
        """
        with open(filepath, "wb") as f:
            f.write(data)

    async def _send_udp_notification(self, filename: str) -> bool:
        """
        Send a UDP notification to Unreal Engine.
        
        Args:
            filename: The filename to send in the notification
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise
        """
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Send filename as message
            message = filename.encode("utf-8")
            
            # Use asyncio to avoid blocking
            await asyncio.to_thread(
                sock.sendto, message, (self.host, self.port)
            )
            
            # No need to wait for response with UDP
            sock.close()
            return True
            
        except Exception as e:
            logger.error(f"Error sending UDP notification: {str(e)}")
            return False

    async def cleanup_old_files(self, max_files: int = 10):
        """
        Clean up old audio files to prevent disk space issues.
        
        Args:
            max_files: Maximum number of files to keep
        """
        if self.use_alternating_files:
            # No cleanup needed for alternating files
            return
            
        try:
            # Get list of audio files
            files = []
            for ext in self.file_extensions:
                pattern = f"audio_output_*.{ext}"
                files.extend(list(Path(self.audio_output_path).glob(pattern)))
            
            # Sort by modification time (oldest first)
            files.sort(key=lambda f: f.stat().st_mtime)
            
            # Delete oldest files if there are too many
            if len(files) > max_files:
                for file in files[:-max_files]:
                    try:
                        file.unlink()
                        logger.debug(f"Deleted old audio file: {file}")
                    except Exception as e:
                        logger.warning(f"Failed to delete file {file}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Error cleaning up old files: {str(e)}")

    async def test_connection(self) -> bool:
        """
        Test the connection to Unreal Engine.
        
        Returns:
            bool: True if the connection test was successful, False otherwise
        """
        try:
            # Send a test message
            return await self._send_udp_notification("TEST_CONNECTION")
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
