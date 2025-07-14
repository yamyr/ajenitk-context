"""MCP transport implementations."""

import asyncio
import json
import sys
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, AsyncIterator
import logging
from asyncio import StreamReader, StreamWriter

from .models import JSONRPCMessage, JSONRPCRequest, JSONRPCResponse, JSONRPCNotification


logger = logging.getLogger(__name__)


class Transport(ABC):
    """Base transport class for MCP communication."""
    
    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message."""
        pass
    
    @abstractmethod
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive a message."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the transport."""
        pass


class StdioTransport(Transport):
    """Standard I/O transport for MCP."""
    
    def __init__(self):
        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None
        self._read_task: Optional[asyncio.Task] = None
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._closed = False
    
    async def start(self):
        """Start the stdio transport."""
        if sys.platform == "win32":
            # Windows-specific event loop policy
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Get stdin/stdout streams
        loop = asyncio.get_event_loop()
        
        # Create reader and writer
        self._reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(self._reader)
        
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        
        transport, _ = await loop.connect_write_pipe(
            lambda: asyncio.Protocol(),
            sys.stdout
        )
        self._writer = asyncio.StreamWriter(transport, protocol, self._reader, loop)
        
        # Start reading messages
        self._read_task = asyncio.create_task(self._read_loop())
    
    async def _read_loop(self):
        """Read messages from stdin."""
        while not self._closed:
            try:
                # Read line from stdin
                line = await self._reader.readline()
                if not line:
                    break
                
                # Parse JSON message
                try:
                    message = json.loads(line.decode().strip())
                    await self._message_queue.put(message)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {e}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading from stdin: {e}")
                break
    
    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message to stdout."""
        if self._closed or not self._writer:
            raise RuntimeError("Transport is closed")
        
        try:
            # Convert to JSON and write
            json_str = json.dumps(message) + "\n"
            self._writer.write(json_str.encode())
            await self._writer.drain()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive a message from stdin."""
        if self._closed:
            return None
        
        try:
            message = await self._message_queue.get()
            return message
        except asyncio.CancelledError:
            return None
    
    async def close(self) -> None:
        """Close the transport."""
        self._closed = True
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()


class SSETransport(Transport):
    """Server-Sent Events transport for MCP."""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self._session = None
        self._closed = False
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._event_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the SSE transport."""
        import aiohttp
        
        self._session = aiohttp.ClientSession()
        self._event_task = asyncio.create_task(self._event_loop())
    
    async def _event_loop(self):
        """Read SSE events."""
        try:
            async with self._session.get(
                self.endpoint,
                headers={"Accept": "text/event-stream"}
            ) as response:
                async for line in response.content:
                    if self._closed:
                        break
                    
                    line = line.decode().strip()
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            message = json.loads(data)
                            await self._message_queue.put(message)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse SSE data: {data}")
                            
        except Exception as e:
            logger.error(f"SSE connection error: {e}")
    
    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message via POST."""
        if self._closed or not self._session:
            raise RuntimeError("Transport is closed")
        
        try:
            async with self._session.post(
                self.endpoint,
                json=message,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive a message from SSE."""
        if self._closed:
            return None
        
        try:
            message = await self._message_queue.get()
            return message
        except asyncio.CancelledError:
            return None
    
    async def close(self) -> None:
        """Close the transport."""
        self._closed = True
        
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
        
        if self._session:
            await self._session.close()


class WebSocketTransport(Transport):
    """WebSocket transport for MCP."""
    
    def __init__(self, url: str):
        self.url = url
        self._websocket = None
        self._closed = False
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._read_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the WebSocket transport."""
        import aiohttp
        
        session = aiohttp.ClientSession()
        self._websocket = await session.ws_connect(self.url)
        self._read_task = asyncio.create_task(self._read_loop())
    
    async def _read_loop(self):
        """Read messages from WebSocket."""
        while not self._closed:
            try:
                msg = await self._websocket.receive()
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        message = json.loads(msg.data)
                        await self._message_queue.put(message)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON: {msg.data}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self._websocket.exception()}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    break
                    
            except Exception as e:
                logger.error(f"Error reading from WebSocket: {e}")
                break
    
    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message via WebSocket."""
        if self._closed or not self._websocket:
            raise RuntimeError("Transport is closed")
        
        try:
            await self._websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive a message from WebSocket."""
        if self._closed:
            return None
        
        try:
            message = await self._message_queue.get()
            return message
        except asyncio.CancelledError:
            return None
    
    async def close(self) -> None:
        """Close the transport."""
        self._closed = True
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self._websocket:
            await self._websocket.close()