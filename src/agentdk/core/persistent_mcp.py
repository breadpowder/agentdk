"""Persistent MCP session manager for AgentDK.

This module provides persistent session management to solve the MCP session persistence
issue described in PERSISTENT_MCP_FIX.md. Instead of creating new sessions for each
tool call, this maintains long-lived async context managers for the agent's lifetime.
"""

import asyncio
import atexit
import signal
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_core.tools import BaseTool
    from mcp import ClientSession

from .logging_config import get_logger


logger = get_logger()


class _PersistentSessionContext:
    """Manages a single persistent session context for one MCP server.

    This class wraps the async context manager lifecycle to keep sessions alive
    for the duration of the agent's lifetime instead of creating ephemeral sessions.
    """

    def __init__(self, mcp_client: "MultiServerMCPClient", server_name: str) -> None:
        """Initialize persistent session context.

        Args:
            mcp_client: The MCP client instance
            server_name: Name of the server to create persistent session for
        """
        self.mcp_client = mcp_client
        self.server_name = server_name
        self.session: Optional["ClientSession"] = None
        self._context_manager: Optional[Any] = None
        self._is_active = False

    async def enter(self) -> None:
        """Enter the async context manager and keep it alive.

        This method enters the async context manager provided by the MCP client
        and stores both the session and context manager for later cleanup.

        Raises:
            Exception: If session creation or initialization fails
        """
        try:
            logger.debug(f"Creating persistent session for server: {self.server_name}")

            # Create the async context manager
            self._context_manager = self.mcp_client.session(self.server_name)

            # Enter the context and keep it alive
            self.session = await self._context_manager.__aenter__()
            
            # Validate session is working by trying to initialize it
            try:
                # Try to list tools as a basic connectivity test
                await self.session.list_tools()
                logger.debug(f"Session validation successful for {self.server_name}")
            except Exception as validation_error:
                logger.warning(
                    f"Session created but validation failed for {self.server_name}: {validation_error}"
                )
                # Continue anyway - some servers might not support list_tools immediately
            
            self._is_active = True
            logger.info(f"Persistent session created for server: {self.server_name}")

        except Exception as e:
            logger.error(
                f"Failed to create persistent session for {self.server_name}: {e}"
            )
            await self._cleanup_on_error()
            raise

    async def exit(self) -> None:
        """Exit the async context manager properly.

        This method ensures the async context manager is properly exited
        and resources are cleaned up.
        """
        if not self._is_active or not self._context_manager:
            return

        try:
            logger.debug(
                f"Cleaning up persistent session for server: {self.server_name}"
            )

            # Properly exit the async context manager
            await self._context_manager.__aexit__(None, None, None)

        except Exception as e:
            logger.warning(f"Error during session cleanup for {self.server_name}: {e}")
        finally:
            self.session = None
            self._context_manager = None
            self._is_active = False
            logger.info(f"Persistent session cleaned up for server: {self.server_name}")

    async def _cleanup_on_error(self) -> None:
        """Clean up resources after an error during session creation."""
        cleanup_errors = []
        
        if self._context_manager:
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception as cleanup_error:
                cleanup_errors.append(str(cleanup_error))
                logger.warning(
                    f"Error during error cleanup for {self.server_name}: {cleanup_error}"
                )

        # Reset state regardless of cleanup success
        self.session = None
        self._context_manager = None
        self._is_active = False
        
        # Log summary if there were cleanup errors
        if cleanup_errors:
            logger.warning(
                f"Session cleanup completed with {len(cleanup_errors)} errors for {self.server_name}"
            )

    @property
    def is_active(self) -> bool:
        """Check if the persistent session is active."""
        return self._is_active and self.session is not None


class PersistentSessionManager:
    """Manages persistent MCP sessions for an agent's lifetime.

    This class wraps the MCP client to maintain long-lived session contexts
    instead of creating ephemeral sessions for each tool call. This solves
    the performance overhead issue described in PERSISTENT_MCP_FIX.md.
    """

    def __init__(self, mcp_client: "MultiServerMCPClient") -> None:
        """Initialize the persistent session manager.

        Args:
            mcp_client: The MCP client to manage sessions for
        """
        self.mcp_client = mcp_client
        self._session_contexts: Dict[str, _PersistentSessionContext] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Create persistent session contexts for all configured servers.

        This method creates and initializes persistent sessions for all servers
        configured in the MCP client. Sessions will remain active until cleanup.

        Raises:
            Exception: If any session fails to initialize
        """
        if self._initialized:
            logger.debug("Persistent session manager already initialized")
            return

        logger.info("Initializing persistent MCP sessions")

        failed_servers = []

        for server_name in self.mcp_client.connections.keys():
            try:
                session_context = _PersistentSessionContext(
                    self.mcp_client, server_name
                )
                await session_context.enter()
                self._session_contexts[server_name] = session_context

            except Exception as e:
                logger.error(f"Failed to initialize session for {server_name}: {e}")
                failed_servers.append(server_name)

        if failed_servers:
            error_msg = f"Failed to initialize MCP sessions for servers: {', '.join(failed_servers)}. Check server connectivity and configuration in MCP config file. Review error logs above for specific server failure details."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        self._initialized = True
        active_sessions = len(
            [ctx for ctx in self._session_contexts.values() if ctx.is_active]
        )
        logger.info(
            f"Persistent session manager initialized with {active_sessions} active sessions"
        )

    async def get_tools_persistent(self) -> List["BaseTool"]:
        """Get tools using persistent sessions instead of ephemeral ones.

        This method creates tools that directly use our persistent sessions,
        avoiding the langchain-mcp-adapters ephemeral session creation that
        causes async context manager corruption.

        Returns:
            List of BaseTool instances that use persistent sessions

        Raises:
            RuntimeError: If manager is not initialized
        """
        if not self._initialized:
            raise RuntimeError(
                "PersistentSessionManager must be initialized before getting tools"
            )

        logger.debug("Creating tools with persistent session support")

        all_tools: List["BaseTool"] = []

        for server_name, session_context in self._session_contexts.items():
            if not session_context.is_active:
                logger.warning(f"Session for {server_name} is not active, skipping")
                continue

            try:
                # Get tool definitions from the session
                tools_result = await session_context.session.list_tools()
                mcp_tools = tools_result.tools if tools_result.tools else []

                # Create custom tools that use our persistent sessions
                for mcp_tool in mcp_tools:
                    persistent_tool = self._create_persistent_tool(
                        server_name, session_context, mcp_tool
                    )
                    all_tools.append(persistent_tool)

                logger.debug(
                    f"Created {len(mcp_tools)} persistent tools from server: {server_name}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to create persistent tools from {server_name}: {e}"
                )
                # Continue with other servers

        logger.info(f"Created total {len(all_tools)} persistent tools")
        return all_tools

    def _create_persistent_tool(
        self,
        server_name: str,
        session_context: "_PersistentSessionContext",
        mcp_tool: Any,
    ) -> "BaseTool":
        """Create a tool that uses persistent sessions instead of ephemeral ones.

        This method creates a LangChain tool that directly calls our persistent session,
        avoiding the async context manager corruption from langchain-mcp-adapters.

        Args:
            server_name: Name of the MCP server
            session_context: Persistent session context
            mcp_tool: MCP tool definition

        Returns:
            BaseTool that uses persistent sessions
        """
        from langchain_core.tools import StructuredTool

        async def persistent_tool_call(**kwargs: Any) -> str:
            """Tool call that uses persistent session directly."""
            try:
                if not session_context.is_active:
                    raise RuntimeError(
                        f"Persistent session for {server_name} is not active"
                    )

                if not session_context.session:
                    raise RuntimeError(f"No session available for {server_name}")

                # Call the tool using our persistent session
                logger.debug(f"Calling tool {mcp_tool.name} with args: {kwargs}")
                result = await session_context.session.call_tool(mcp_tool.name, kwargs)
                logger.debug(f"Tool {mcp_tool.name} returned: {result}")

                # Check for errors in the result
                if hasattr(result, "isError") and result.isError:
                    error_msg = "Unknown error"
                    if result.content:
                        error_parts = []
                        for content in result.content:
                            if hasattr(content, "text"):
                                error_parts.append(content.text)
                            else:
                                error_parts.append(str(content))
                        if error_parts:
                            error_msg = "\n".join(error_parts)
                    raise RuntimeError(f"Tool execution error: {error_msg}")

                # Extract text content from the result
                if result.content:
                    text_parts = []
                    for content in result.content:
                        if hasattr(content, "text"):
                            text_parts.append(content.text)
                        else:
                            text_parts.append(str(content))

                    if len(text_parts) == 1:
                        return text_parts[0]
                    elif text_parts:
                        return "\n".join(text_parts)

                return "Tool executed successfully"

            except Exception as e:
                error_msg = str(e) if str(e) else "Unknown error occurred"
                logger.error(
                    f"Persistent tool call failed for {mcp_tool.name}: {error_msg}"
                )
                return f"Tool execution failed: {error_msg}"

        # Create the tool with persistent session support
        return StructuredTool(
            name=mcp_tool.name,
            description=mcp_tool.description or f"Tool from {server_name} server",
            args_schema=(
                mcp_tool.inputSchema if hasattr(mcp_tool, "inputSchema") else None
            ),
            coroutine=persistent_tool_call,
            response_format=(
                "content_and_artifact"
                if hasattr(mcp_tool, "annotations")
                else "content"
            ),
        )

    async def cleanup(self) -> None:
        """Clean up all persistent session contexts.

        This method properly exits all async context managers and cleans up
        resources. Should be called when the agent is being destroyed.
        """
        if not self._initialized:
            return

        logger.info("Cleaning up persistent MCP sessions")

        cleanup_tasks = []
        for server_name, session_context in self._session_contexts.items():
            cleanup_tasks.append(session_context.exit())

        # Wait for all cleanups to complete
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self._session_contexts.clear()
        self._initialized = False

        logger.info("All persistent MCP sessions cleaned up")

    @property
    def is_initialized(self) -> bool:
        """Check if the session manager is initialized."""
        return self._initialized

    @property
    def active_session_count(self) -> int:
        """Get the number of active sessions."""
        return len([ctx for ctx in self._session_contexts.values() if ctx.is_active])


class CleanupManager:
    """Handles cleanup across different Python environments.

    This class provides comprehensive cleanup strategies for different Python
    environments including standard Python, IPython/Jupyter, and process signals.
    """

    def __init__(self, persistent_session_manager: PersistentSessionManager) -> None:
        """Initialize cleanup manager.

        Args:
            persistent_session_manager: The session manager to clean up
        """
        self.session_manager = persistent_session_manager
        self._cleanup_registered = False
        self._cleanup_in_progress = False

    def register_cleanup(self) -> None:
        """Register cleanup handlers for different environments.

        This method registers cleanup handlers for:
        - Standard Python atexit
        - Process signals (SIGTERM, SIGINT)
        - IPython/Jupyter environments (if available)
        """
        if self._cleanup_registered:
            logger.debug("Cleanup handlers already registered")
            return

        logger.debug("Registering cleanup handlers")

        # Standard Python atexit
        atexit.register(self._sync_cleanup)

        # Signal handlers for graceful shutdown
        try:
            signal.signal(signal.SIGTERM, self._signal_cleanup)
            signal.signal(signal.SIGINT, self._signal_cleanup)
        except (OSError, ValueError) as e:
            # Signal registration might fail in some environments (like Windows)
            logger.debug(f"Could not register signal handlers: {e}")

        # IPython/Jupyter cleanup
        self._register_ipython_cleanup()

        self._cleanup_registered = True
        logger.info("Cleanup handlers registered successfully")

    def _register_ipython_cleanup(self) -> None:
        """Register cleanup for IPython/Jupyter environments."""
        try:
            from IPython import get_ipython

            ipython = get_ipython()
            if ipython:
                # Register cleanup to run when IPython shuts down
                ipython.atexit(self._ipython_cleanup)
                logger.debug("IPython cleanup handler registered")
        except ImportError:
            logger.debug("IPython not available, skipping IPython cleanup registration")
        except Exception as e:
            logger.debug(f"Could not register IPython cleanup: {e}")

    def _sync_cleanup(self) -> None:
        """Synchronous cleanup for atexit and signal handlers."""
        if self._cleanup_in_progress:
            return

        self._cleanup_in_progress = True

        try:
            logger.debug("Running synchronous cleanup")

            # Try to run async cleanup
            try:
                # Check if there's already an event loop running
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running (like in Jupyter), create a task
                    asyncio.create_task(self.session_manager.cleanup())
                else:
                    # If no loop is running, run the cleanup
                    loop.run_until_complete(self.session_manager.cleanup())
            except RuntimeError:
                # No event loop, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.session_manager.cleanup())
                finally:
                    loop.close()

        except Exception as e:
            logger.warning(f"Warning: MCP session cleanup failed: {e}")
        finally:
            self._cleanup_in_progress = False

    def _signal_cleanup(self, signum: int, frame: Any) -> None:
        """Signal handler cleanup.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, cleaning up MCP sessions")
        self._sync_cleanup()

    def _ipython_cleanup(self) -> None:
        """IPython-specific cleanup handler."""
        logger.debug("Running IPython cleanup")
        try:
            # In IPython, we can use asyncio.create_task if loop is running
            asyncio.create_task(self.session_manager.cleanup())
        except Exception as e:
            logger.warning(f"IPython cleanup failed: {e}")
            # Fallback to sync cleanup
            self._sync_cleanup()
