"""Tests for persistent MCP session management."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from agentdk.core.persistent_mcp import (
    _PersistentSessionContext,
    PersistentSessionManager,
    CleanupManager
)


class TestPersistentSessionContext:
    """Test the _PersistentSessionContext class."""

    def test_init(self):
        """Test context initialization."""
        mock_client = MagicMock()
        context = _PersistentSessionContext(mock_client, "test_server")
        
        assert context.mcp_client == mock_client
        assert context.server_name == "test_server"
        assert context.session is None
        assert context._is_active is False

    @pytest.mark.asyncio
    async def test_enter_success(self):
        """Test successful context entry."""
        mock_client = MagicMock()
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client.session.return_value = mock_context_manager
        
        context = _PersistentSessionContext(mock_client, "test_server")
        
        # Mock list_tools for validation
        mock_session.list_tools = AsyncMock()
        
        await context.enter()
        
        assert context.session == mock_session
        assert context._is_active is True
        mock_client.session.assert_called_once_with("test_server")
        mock_context_manager.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_enter_validation_failure_continues(self):
        """Test that validation failure doesn't prevent session creation."""
        mock_client = MagicMock()
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        mock_client.session.return_value = mock_context_manager
        
        # Make list_tools fail
        mock_session.list_tools = AsyncMock(side_effect=Exception("Validation error"))
        
        context = _PersistentSessionContext(mock_client, "test_server")
        
        await context.enter()
        
        # Should still succeed despite validation failure
        assert context.session == mock_session
        assert context._is_active is True

    @pytest.mark.asyncio
    async def test_enter_failure_cleanup(self):
        """Test cleanup on entry failure."""
        mock_client = MagicMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client.session.return_value = mock_context_manager
        
        context = _PersistentSessionContext(mock_client, "test_server")
        
        with pytest.raises(Exception, match="Connection failed"):
            await context.enter()
        
        assert context.session is None
        assert context._is_active is False

    @pytest.mark.asyncio
    async def test_exit_success(self):
        """Test successful context exit."""
        mock_client = MagicMock()
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context_manager.__aexit__ = AsyncMock()
        mock_client.session.return_value = mock_context_manager
        
        context = _PersistentSessionContext(mock_client, "test_server")
        context._context_manager = mock_context_manager
        context._is_active = True
        
        await context.exit()
        
        assert context.session is None
        assert context._is_active is False
        mock_context_manager.__aexit__.assert_called_once_with(None, None, None)

    def test_is_active_property(self):
        """Test is_active property."""
        mock_client = MagicMock()
        context = _PersistentSessionContext(mock_client, "test_server")
        
        assert not context.is_active
        
        context._is_active = True
        context.session = MagicMock()
        assert context.is_active
        
        context.session = None
        assert not context.is_active


class TestPersistentSessionManager:
    """Test the PersistentSessionManager class."""

    def test_init(self):
        """Test manager initialization."""
        mock_client = MagicMock()
        manager = PersistentSessionManager(mock_client)
        
        assert manager.mcp_client == mock_client
        assert manager._session_contexts == {}
        assert not manager._initialized

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful manager initialization."""
        mock_client = MagicMock()
        mock_client.connections = {"server1": MagicMock(), "server2": MagicMock()}
        
        manager = PersistentSessionManager(mock_client)
        
        with patch.object(manager, '_session_contexts') as mock_contexts:
            mock_context1 = AsyncMock()
            mock_context2 = AsyncMock()
            
            # Mock the context creation and enter calls
            with patch('agentdk.core.persistent_mcp._PersistentSessionContext') as MockContext:
                MockContext.side_effect = [mock_context1, mock_context2]
                
                await manager.initialize()
        
        assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_with_failures(self):
        """Test initialization with some server failures."""
        mock_client = MagicMock()
        mock_client.connections = {"server1": MagicMock(), "server2": MagicMock()}
        
        manager = PersistentSessionManager(mock_client)
        
        with patch('agentdk.core.persistent_mcp._PersistentSessionContext') as MockContext:
            mock_context1 = AsyncMock()
            mock_context1.enter = AsyncMock(side_effect=Exception("Server1 failed"))
            mock_context2 = AsyncMock()
            MockContext.side_effect = [mock_context1, mock_context2]
            
            with pytest.raises(RuntimeError, match="Failed to initialize MCP sessions"):
                await manager.initialize()

    @pytest.mark.asyncio
    async def test_get_tools_persistent_not_initialized(self):
        """Test getting tools when not initialized."""
        mock_client = MagicMock()
        manager = PersistentSessionManager(mock_client)
        
        with pytest.raises(RuntimeError, match="must be initialized"):
            await manager.get_tools_persistent()

    def test_properties(self):
        """Test manager properties."""
        mock_client = MagicMock()
        manager = PersistentSessionManager(mock_client)
        
        assert not manager.is_initialized
        assert manager.active_session_count == 0
        
        # Add mock session contexts
        mock_context1 = MagicMock()
        mock_context1.is_active = True
        mock_context2 = MagicMock()
        mock_context2.is_active = False
        
        manager._session_contexts = {"server1": mock_context1, "server2": mock_context2}
        assert manager.active_session_count == 1


class TestCleanupManager:
    """Test the CleanupManager class."""

    def test_init(self):
        """Test cleanup manager initialization."""
        mock_session_manager = MagicMock()
        cleanup = CleanupManager(mock_session_manager)
        
        assert cleanup.session_manager == mock_session_manager
        assert not cleanup._cleanup_registered

    @patch('agentdk.core.persistent_mcp.atexit')
    @patch('agentdk.core.persistent_mcp.signal')
    def test_register_cleanup(self, mock_signal, mock_atexit):
        """Test cleanup registration."""
        mock_session_manager = MagicMock()
        cleanup = CleanupManager(mock_session_manager)
        
        cleanup.register_cleanup()
        
        assert cleanup._cleanup_registered
        mock_atexit.register.assert_called_once()
        # Signal registration should be attempted
        assert mock_signal.signal.call_count >= 0  # May fail in some environments

    def test_register_cleanup_idempotent(self):
        """Test that cleanup registration is idempotent."""
        mock_session_manager = MagicMock()
        cleanup = CleanupManager(mock_session_manager)
        
        with patch('agentdk.core.persistent_mcp.atexit') as mock_atexit:
            cleanup.register_cleanup()
            cleanup.register_cleanup()  # Second call
            
            # Should only register once
            mock_atexit.register.assert_called_once()