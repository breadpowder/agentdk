"""Persistent MCP session management to avoid subprocess termination issues."""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager


class PersistentMCPManager:
    """Manages persistent MCP sessions to avoid subprocess termination.
    
    This class addresses the issue where langchain-mcp-adapters creates
    ephemeral sessions for each tool call, causing MCP servers to terminate
    and lose state between operations.
    """
    
    def __init__(self, client_config: Dict[str, Any]):
        """Initialize the persistent MCP manager.
        
        Args:
            client_config: Configuration dictionary for MCP servers
        """
        self.client_config = client_config
        self._sessions: Dict[str, Any] = {}  # server_name -> client (for compatibility)
        self._clients: Dict[str, Any] = {}   # server_name -> client
        self._locks: Dict[str, asyncio.Lock] = {}  # server_name -> lock
        self.logger = logging.getLogger(__name__)
        
    async def get_session(self, server_name: str):
        """Get or create persistent session for server.
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            Active session for the server
        """
        if server_name not in self._locks:
            self._locks[server_name] = asyncio.Lock()
            
        async with self._locks[server_name]:
            # Check if existing session is still valid
            if server_name in self._sessions:
                try:
                    # Try to validate the session by checking if it's still active
                    session = self._sessions[server_name]
                    if hasattr(session, '_transport') and hasattr(session._transport, 'is_closed'):
                        if session._transport.is_closed():
                            self.logger.warning(f"Session for {server_name} is closed, recreating...")
                            await self._cleanup_session(server_name)
                        else:
                            return session
                    else:
                        return session
                except Exception as e:
                    self.logger.warning(f"Session validation failed for {server_name}: {e}, recreating...")
                    await self._cleanup_session(server_name)
            
            # Create new session
            await self._create_session(server_name)
            return self._sessions[server_name]
    
    async def _create_session(self, server_name: str):
        """Create new client for server (not truly persistent to avoid generator issues).
        
        Args:
            server_name: Name of the MCP server
        """
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
            
            # Create client for this specific server
            server_config = {server_name: self.client_config[server_name]}
            client = MultiServerMCPClient(server_config)
            
            # Store client (not session to avoid async generator conflicts)
            self._clients[server_name] = client
            self._sessions[server_name] = client  # Store client as "session" for compatibility
            
            self.logger.info(f"Created MCP client for server: {server_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to create client for {server_name}: {e}")
            raise
    
    async def call_tool(self, server_name: str, tool_name: str, **kwargs):
        """Call a tool using session context manager to avoid generator issues.
        
        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to call
            **kwargs: Tool arguments
            
        Returns:
            Tool execution result
        """
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Get client (stored as "session" for compatibility)
                client = await self.get_session(server_name)
                
                # Use proper session context manager to avoid generator conflicts
                async with client.session(server_name) as session:
                    result = await session.call_tool(tool_name, kwargs)
                    return result
                    
            except Exception as e:
                self.logger.error(f"Tool call attempt {attempt + 1} failed for {tool_name}: {e}")
                
                if attempt == max_retries - 1:  # Last attempt
                    # Don't retry anymore, raise a clear error
                    raise RuntimeError(f"Tool '{tool_name}' failed after {max_retries} attempts. Last error: {e}")
                
                # Clean up the broken client before retry
                if server_name in self._sessions:
                    try:
                        await self._cleanup_session(server_name)
                    except Exception as cleanup_error:
                        self.logger.warning(f"Error during session cleanup: {cleanup_error}")
                
                # Wait before retry
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
    
    async def list_tools(self, server_name: str):
        """List tools from a server using persistent session.
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            List of available tools
        """
        session = await self.get_session(server_name)
        return await session.list_tools()
    
    async def cleanup(self):
        """Cleanup all persistent sessions."""
        for server_name in list(self._sessions.keys()):
            await self._cleanup_session(server_name)
    
    async def _cleanup_session(self, server_name: str):
        """Cleanup a specific client/session.
        
        Args:
            server_name: Name of the MCP server
        """
        try:
            # Clean up references (no complex async generator cleanup needed)
            if server_name in self._sessions:
                del self._sessions[server_name]
            if server_name in self._clients:
                del self._clients[server_name]
            # Don't delete locks as they might be needed for concurrent access
                
            self.logger.info(f"Cleaned up client for MCP server: {server_name}")
            
        except Exception as e:
            self.logger.warning(f"Error cleaning up client for {server_name}: {e}")
            # Force cleanup of references
            self._sessions.pop(server_name, None)
            self._clients.pop(server_name, None)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()


def create_persistent_tool(tool_schema, server_name: str, manager: PersistentMCPManager):
    """Create a LangChain StructuredTool that uses persistent MCP sessions.
    
    Args:
        tool_schema: Tool schema from MCP server
        server_name: Name of the MCP server
        manager: Persistent MCP manager instance
        
    Returns:
        LangChain StructuredTool instance
    """
    async def persistent_tool_func(**kwargs):
        """Execute tool using persistent session."""
        try:
            return await manager.call_tool(server_name, tool_schema.name, **kwargs)
        except Exception as e:
            # Log the error with more context and re-raise with a clearer message
            logger = logging.getLogger(__name__)
            logger.error(f"Tool '{tool_schema.name}' execution failed: {e}")
            
            # Don't just re-raise the generic exception, create a more specific one
            # This helps prevent LangGraph from endlessly retrying
            if "failed after" in str(e):
                # This is already our retry error, don't wrap it again
                raise
            else:
                # Wrap with a clear error message
                raise RuntimeError(f"Tool '{tool_schema.name}' failed: {e}") from e
    
    # Create proper LangChain StructuredTool
    try:
        from langchain_core.tools import StructuredTool
        
        return StructuredTool(
            name=tool_schema.name,
            description=tool_schema.description,
            args_schema=getattr(tool_schema, 'args_schema', None),
            coroutine=persistent_tool_func  # Use coroutine for async tools
        )
    except ImportError:
        try:
            # Fallback to older import path
            from langchain.tools import StructuredTool
            
            return StructuredTool(
                name=tool_schema.name,
                description=tool_schema.description,
                args_schema=getattr(tool_schema, 'args_schema', None),
                func=persistent_tool_func
            )
        except ImportError:
            # Final fallback: create a minimal tool-like object
            class MinimalTool:
                def __init__(self, name, description, func, args_schema=None):
                    self.name = name
                    self.description = description
                    self.args_schema = args_schema
                    self.func = func
                    self.coroutine = func
                    self.__name__ = name  # Important for LangGraph
                    
                async def arun(self, **kwargs):
                    return await self.func(**kwargs)
                    
                def run(self, **kwargs):
                    return asyncio.run(self.arun(**kwargs))
            
            return MinimalTool(
                tool_schema.name,
                tool_schema.description, 
                persistent_tool_func,
                getattr(tool_schema, 'args_schema', None)
            )


async def create_persistent_tools(client_config: Dict[str, Any]) -> List[Any]:
    """Create persistent MCP tools from client configuration.
    
    Args:
        client_config: Configuration dictionary for MCP servers
        
    Returns:
        List of LangChain StructuredTool instances
    """
    manager = PersistentMCPManager(client_config)
    tools = []
    
    try:
        # Import here to avoid circular imports
        from langchain_mcp_adapters.client import MultiServerMCPClient
        
        # Get tool schemas from each server
        for server_name, server_config in client_config.items():
            try:
                # Use temporary client to get tool schemas
                temp_client = MultiServerMCPClient({server_name: server_config})
                temp_tools = await temp_client.get_tools()
                
                # Create persistent tools using StructuredTool
                for tool_schema in temp_tools:
                    persistent_tool = create_persistent_tool(
                        tool_schema, server_name, manager
                    )
                    tools.append(persistent_tool)
                    
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to load tools from {server_name}: {e}")
                continue
                
    except ImportError as e:
        logging.getLogger(__name__).error(f"langchain-mcp-adapters not available: {e}")
        
    return tools