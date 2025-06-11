"""
Twitch Chat Client module for AI-Powered MetaHuman Avatar System.

This module provides an asynchronous IRC client for connecting to Twitch chat,
parsing messages, and handling events like PING/PONG for connection maintenance.
"""

import asyncio
import logging
import re
import socket
import ssl
import time
from typing import Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class TwitchChatClient:
    """
    Asynchronous Twitch IRC client that connects to chat and processes messages.
    
    This client handles the Twitch IRC protocol, including authentication,
    channel joining, message parsing, and PING/PONG responses.
    """

    def __init__(
        self,
        token: str,
        username: str,
        channel: str,
        use_ssl: bool = True,
        host: str = "irc.chat.twitch.tv",
        port: int = None,
        reconnect_delay: int = 5,
    ):
        """
        Initialize the Twitch chat client.
        
        Args:
            token: OAuth token for authentication (without 'oauth:' prefix)
            username: Twitch username for the bot
            channel: Channel name to join (without '#' prefix)
            use_ssl: Whether to use SSL for the connection
            host: Twitch IRC server hostname
            port: Port number (defaults to 6697 for SSL, 6667 for non-SSL)
            reconnect_delay: Seconds to wait before reconnecting after disconnect
        """
        self.token = token if token.startswith("oauth:") else f"oauth:{token}"
        self.username = username.lower()
        self.channel = channel.lower() if channel.startswith("#") else f"#{channel.lower()}"
        self.host = host
        self.use_ssl = use_ssl
        self.port = port or (6697 if use_ssl else 6667)
        self.reconnect_delay = reconnect_delay
        
        # Connection state
        self.reader = None
        self.writer = None
        self.running = False
        self.connected = False
        self.last_ping_time = 0
        
        # Callbacks
        self.on_message: Optional[Callable[[str, str], None]] = None
        self.on_connect: Optional[Callable[[], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None
        
        # Message parsing regex
        self._privmsg_regex = re.compile(
            r":(?P<username>[^!]+)!(?P=username)@(?P=username)\.tmi\.twitch\.tv PRIVMSG "
            r"#\w+ :(?P<message>.*)"
        )
        self._tags_regex = re.compile(
            r"@.*display-name=(?P<display_name>[^;]*).*:(?P<username>[^!]+)!.*PRIVMSG "
            r"#\w+ :(?P<message>.*)"
        )

    async def connect(self) -> bool:
        """
        Connect to Twitch IRC server.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            logger.info(f"Connecting to {self.host}:{self.port}")
            
            # Create connection
            if self.use_ssl:
                ssl_context = ssl.create_default_context()
                reader, writer = await asyncio.open_connection(
                    self.host, self.port, ssl=ssl_context
                )
            else:
                reader, writer = await asyncio.open_connection(self.host, self.port)
            
            self.reader = reader
            self.writer = writer
            
            # Send authentication
            await self._send_command(f"PASS {self.token}")
            await self._send_command(f"NICK {self.username}")
            
            # Request capabilities for tags (optional)
            await self._send_command("CAP REQ :twitch.tv/tags twitch.tv/commands")
            
            # Join channel
            await self._send_command(f"JOIN {self.channel}")
            
            # Read welcome messages
            async for line in self._read_lines():
                logger.debug(f"< {line}")
                
                # Check for successful connection
                if f":{self.host} 001" in line:
                    logger.info("Successfully authenticated with Twitch IRC")
                
                # Check for successful channel join
                if f":{self.username}.tmi.twitch.tv JOIN {self.channel}" in line:
                    logger.info(f"Successfully joined channel {self.channel}")
                    self.connected = True
                    if self.on_connect:
                        await asyncio.create_task(self._safe_callback(self.on_connect))
                    return True
                
                # Check for auth failure
                if "authentication failed" in line.lower() or "improperly formatted auth" in line.lower():
                    logger.error("Authentication failed. Check your OAuth token.")
                    return False
                
                # Stop after receiving enough welcome messages
                if line.startswith(f":{self.host} 366"):
                    self.connected = True
                    if self.on_connect:
                        await asyncio.create_task(self._safe_callback(self.on_connect))
                    return True
            
            return False
            
        except (OSError, asyncio.TimeoutError) as e:
            logger.error(f"Connection error: {str(e)}")
            return False

    async def disconnect(self):
        """Disconnect from Twitch IRC server."""
        self.running = False
        if self.connected and self.writer:
            try:
                await self._send_command(f"PART {self.channel}")
                await self._send_command("QUIT")
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f"Error during disconnect: {str(e)}")
            finally:
                self.connected = False
                if self.on_disconnect:
                    await asyncio.create_task(self._safe_callback(self.on_disconnect))
                logger.info("Disconnected from Twitch IRC")

    async def connect_and_listen(self):
        """
        Connect to Twitch IRC and start listening for messages.
        
        This method will attempt to reconnect if the connection is lost.
        """
        self.running = True
        
        while self.running:
            if not self.connected:
                connected = await self.connect()
                if not connected:
                    logger.warning(f"Connection failed, retrying in {self.reconnect_delay} seconds...")
                    await asyncio.sleep(self.reconnect_delay)
                    continue
            
            try:
                await self._listen_for_messages()
            except (OSError, asyncio.CancelledError, ConnectionError) as e:
                logger.error(f"Connection error: {str(e)}")
                self.connected = False
                if self.on_disconnect:
                    await asyncio.create_task(self._safe_callback(self.on_disconnect))
                
                if self.running:
                    logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
                    await asyncio.sleep(self.reconnect_delay)

    async def _listen_for_messages(self):
        """Listen for and process incoming IRC messages."""
        if not self.reader:
            raise ConnectionError("Not connected to IRC server")
        
        async for line in self._read_lines():
            line = line.strip()
            if not line:
                continue
                
            logger.debug(f"< {line}")
            
            # Handle PING messages
            if line.startswith("PING"):
                await self._send_command("PONG :tmi.twitch.tv")
                self.last_ping_time = time.time()
                continue
                
            # Handle PRIVMSG (chat messages)
            if "PRIVMSG" in line:
                username, message = self._parse_message(line)
                if username and message and self.on_message:
                    await asyncio.create_task(self._safe_callback(self.on_message, username, message))

    async def _read_lines(self):
        """
        Read lines from the IRC connection.
        
        Yields:
            str: Each line received from the IRC server
        """
        buffer = ""
        while self.connected and self.reader:
            try:
                data = await self.reader.read(4096)
                if not data:
                    logger.warning("Connection closed by server")
                    self.connected = False
                    break
                    
                buffer += data.decode("utf-8", errors="ignore")
                
                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    yield line
                    
            except (UnicodeDecodeError, asyncio.CancelledError) as e:
                logger.error(f"Error reading from IRC: {str(e)}")
                if isinstance(e, asyncio.CancelledError):
                    raise

    async def _send_command(self, command: str):
        """
        Send an IRC command to the server.
        
        Args:
            command: The IRC command to send
        """
        if not self.writer:
            logger.error("Cannot send command: not connected")
            return
            
        try:
            self.writer.write(f"{command}\r\n".encode("utf-8"))
            await self.writer.drain()
            logger.debug(f"> {command}")
        except Exception as e:
            logger.error(f"Error sending command: {str(e)}")
            raise

    def _parse_message(self, line: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse a PRIVMSG line to extract username and message.
        
        Args:
            line: The IRC message line
            
        Returns:
            Tuple containing (username, message) or (None, None) if parsing fails
        """
        # Try parsing with tags first
        if line.startswith('@'):
            match = self._tags_regex.match(line)
            if match:
                display_name = match.group('display_name')
                username = match.group('username')
                message = match.group('message')
                # Use display name if available, otherwise username
                return display_name or username, message
        
        # Try standard IRC format
        match = self._privmsg_regex.match(line)
        if match:
            return match.group('username'), match.group('message')
            
        # Fallback to simpler parsing if regex fails
        try:
            if "PRIVMSG" in line:
                # Extract username
                username_part = line.split('!')[0]
                if username_part.startswith(':'):
                    username = username_part[1:]
                else:
                    username = username_part
                
                # Extract message
                message = line.split(f"PRIVMSG {self.channel} :")[1]
                
                return username, message
        except (IndexError, ValueError):
            pass
            
        logger.debug(f"Failed to parse message: {line}")
        return None, None

    async def _safe_callback(self, callback, *args, **kwargs):
        """
        Safely execute a callback function, catching any exceptions.
        
        Args:
            callback: The callback function to execute
            *args: Arguments to pass to the callback
            **kwargs: Keyword arguments to pass to the callback
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in callback: {str(e)}")
