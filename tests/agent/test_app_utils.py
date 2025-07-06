"""Tests for agentdk.agent.app_utils module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from agentdk.agent.app_utils import (
    extract_response,
    format_memory_context,
    create_supervisor_workflow,
    prepare_query_with_memory,
    create_workflow_messages
)


class TestExtractResponse:
    """Test the extract_response function."""
    
    def test_extract_from_dict_with_aimessage(self):
        """Test extracting response from dict with AIMessage objects."""
        # Mock AIMessage-like object
        mock_message = Mock()
        mock_message.content = "Hello world"
        
        result = {"messages": [mock_message]}
        response = extract_response(result)
        
        assert response == "Hello world"
    
    def test_extract_from_dict_with_dict_message(self):
        """Test extracting response from dict with dict format messages."""
        result = {
            "messages": [
                {"content": "First message", "role": "user"},
                {"content": "Last message", "role": "assistant"}
            ]
        }
        response = extract_response(result)
        
        assert response == "Last message"
    
    def test_extract_from_empty_messages(self):
        """Test extracting from dict with empty messages list."""
        result = {"messages": []}
        response = extract_response(result)
        
        # Should fallback to string representation
        assert response == "{'messages': []}"
    
    def test_extract_from_direct_string(self):
        """Test extracting from direct string result."""
        result = "Direct string response"
        response = extract_response(result)
        
        assert response == "Direct string response"
    
    def test_extract_from_list_with_aimessage(self):
        """Test extracting from list of AIMessage objects."""
        mock_message = Mock()
        mock_message.content = "List message content"
        
        result = [Mock(), mock_message]  # Last item has content
        response = extract_response(result)
        
        assert response == "List message content"
    
    def test_extract_from_list_with_dict_message(self):
        """Test extracting from list of dict messages."""
        result = [
            {"content": "First", "role": "user"},
            {"content": "Last", "role": "assistant"}
        ]
        response = extract_response(result)
        
        assert response == "Last"
    
    def test_extract_from_empty_list(self):
        """Test extracting from empty list."""
        result = []
        response = extract_response(result)
        
        # Should fallback to string representation
        assert response == "[]"
    
    def test_extract_unexpected_message_format(self):
        """Test extracting with unexpected message format logs warning."""
        result = {"messages": [123]}  # Unexpected format
        
        with patch('agentdk.agent.app_utils.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            response = extract_response(result)
            
            # Should log warnings (may be multiple calls)
            assert mock_logger.warning.call_count >= 1
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any("Unexpected message format" in call for call in warning_calls)
            assert response == "{'messages': [123]}"
    
    def test_extract_fallback_with_warning(self):
        """Test fallback behavior with warning for unknown types."""
        result = 12345  # Unexpected type
        
        with patch('agentdk.agent.app_utils.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            response = extract_response(result)
            
            # Should log warning and convert to string
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "Using fallback string conversion" in warning_msg
            assert response == "12345"
    
    def test_extract_from_complex_nested_result(self):
        """Test extracting from complex nested result structure."""
        # Complex LangGraph result with nested structure
        mock_message = Mock()
        mock_message.content = "Complex response"
        
        result = {
            "messages": [
                {"content": "User input", "role": "user"},
                mock_message
            ],
            "other_data": {"metadata": "value"}
        }
        
        response = extract_response(result)
        assert response == "Complex response"


class TestFormatMemoryContext:
    """Test the format_memory_context function."""
    
    def test_format_empty_context(self):
        """Test formatting empty memory context."""
        result = format_memory_context({})
        assert result == ""
        
        result = format_memory_context(None)
        assert result == ""
    
    def test_format_recent_conversation(self):
        """Test formatting recent conversation."""
        memory_context = {
            "recent_conversation": ["Query: tables", "Response: Found 5 tables"]
        }
        
        result = format_memory_context(memory_context)
        
        assert "Recent conversation:" in result
        assert "Query: tables" in result
        assert "Response: Found 5 tables" in result
    
    def test_format_user_preferences(self):
        """Test formatting user preferences."""
        memory_context = {
            "user_preferences": {"format": "table", "limit": 10}
        }
        
        result = format_memory_context(memory_context)
        
        assert "User preferences:" in result
        assert "format: table" in result
        assert "limit: 10" in result
    
    def test_format_relevant_facts(self):
        """Test formatting relevant facts."""
        memory_context = {
            "relevant_facts": ["User works with financial data", "Prefers SQL queries"]
        }
        
        result = format_memory_context(memory_context)
        
        assert "Relevant context:" in result
        assert "User works with financial data" in result
        assert "Prefers SQL queries" in result
    
    def test_format_working_memory_string(self):
        """Test formatting working memory as string."""
        memory_context = {
            "working_memory": "Current analysis context"
        }
        
        result = format_memory_context(memory_context)
        
        assert "Current session context:" in result
        assert "Current analysis context" in result
    
    def test_format_working_memory_list(self):
        """Test formatting working memory as list."""
        memory_context = {
            "working_memory": ["Context item 1", "Context item 2"]
        }
        
        result = format_memory_context(memory_context)
        
        assert "Current session context:" in result
        assert "Context item 1" in result
        assert "Context item 2" in result
    
    def test_format_all_sections(self):
        """Test formatting all memory context sections."""
        memory_context = {
            "recent_conversation": ["Query: show tables"],
            "user_preferences": {"format": "json"},
            "relevant_facts": ["User is analyst"],
            "working_memory": ["Current session"]
        }
        
        result = format_memory_context(memory_context)
        
        assert "Recent conversation:" in result
        assert "User preferences:" in result
        assert "Relevant context:" in result
        assert "Current session context:" in result
        assert "Query: show tables" in result
        assert "format: json" in result
        assert "User is analyst" in result
        assert "Current session" in result
    
    def test_format_empty_sections(self):
        """Test formatting when sections are empty."""
        memory_context = {
            "recent_conversation": [],
            "user_preferences": {},
            "relevant_facts": None,
            "working_memory": ""
        }
        
        result = format_memory_context(memory_context)
        
        # Should not include headers for empty sections
        assert "Recent conversation:" not in result
        assert "User preferences:" not in result
        assert "Relevant context:" not in result
        assert "Current session context:" not in result
    
    def test_format_line_joining(self):
        """Test that lines are properly joined with newlines."""
        memory_context = {
            "user_preferences": {"key": "value"},
            "relevant_facts": ["fact1", "fact2"]
        }
        
        result = format_memory_context(memory_context)
        lines = result.split("\\n")
        
        assert len(lines) > 1
        assert "User preferences:" in lines
        assert "Relevant context:" in lines


class TestCreateSupervisorWorkflow:
    """Test the create_supervisor_workflow function."""
    
    def test_create_supervisor_success(self):
        """Test successful supervisor workflow creation."""
        mock_agents = [Mock(), Mock()]
        mock_model = Mock()
        mock_prompt = "You are a supervisor"
        
        mock_workflow = Mock()
        mock_app = Mock()
        mock_workflow.compile.return_value = mock_app
        
        with patch('agentdk.agent.app_utils.get_logger') as mock_get_logger, \
             patch('langgraph_supervisor.create_supervisor', return_value=mock_workflow) as mock_create:
            
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            result = create_supervisor_workflow(mock_agents, mock_model, mock_prompt)
            
            # Verify supervisor creation
            mock_create.assert_called_once_with(mock_agents, model=mock_model, prompt=mock_prompt)
            mock_workflow.compile.assert_called_once()
            
            # Verify logging
            mock_logger.info.assert_called_once()
            log_msg = mock_logger.info.call_args[0][0]
            assert "Created supervisor workflow with 2 agents" in log_msg
            
            assert result == mock_app
    
    def test_create_supervisor_import_error(self):
        """Test supervisor workflow creation with import error."""
        mock_agents = [Mock()]
        mock_model = Mock()
        mock_prompt = "Test prompt"
        
        with patch('agentdk.agent.app_utils.get_logger') as mock_get_logger, \
             patch('langgraph_supervisor.create_supervisor', side_effect=ImportError("No module")):
            
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with pytest.raises(ImportError) as exc_info:
                create_supervisor_workflow(mock_agents, mock_model, mock_prompt)
            
            # Verify error message
            assert "langgraph_supervisor is required" in str(exc_info.value)
            assert "pip install langgraph langgraph-supervisor" in str(exc_info.value)
            
            # Verify error logging
            mock_logger.error.assert_called_once()
            error_msg = mock_logger.error.call_args[0][0]
            assert "Missing required dependency" in error_msg
    
    def test_create_supervisor_general_error(self):
        """Test supervisor workflow creation with general error."""
        mock_agents = [Mock()]
        mock_model = Mock()
        mock_prompt = "Test prompt"
        
        mock_workflow = Mock()
        mock_workflow.compile.side_effect = Exception("Compilation failed")
        
        with patch('agentdk.agent.app_utils.get_logger') as mock_get_logger, \
             patch('langgraph_supervisor.create_supervisor', return_value=mock_workflow):
            
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            with pytest.raises(Exception, match="Compilation failed"):
                create_supervisor_workflow(mock_agents, mock_model, mock_prompt)
            
            # Verify error logging
            mock_logger.error.assert_called_once()
            error_msg = mock_logger.error.call_args[0][0]
            assert "Failed to create supervisor workflow" in error_msg


class TestPrepareQueryWithMemory:
    """Test the prepare_query_with_memory function."""
    
    def test_prepare_query_no_memory(self):
        """Test preparing query with no memory context."""
        query = "Show tables"
        result = prepare_query_with_memory(query, {})
        
        assert result == query
        
        result = prepare_query_with_memory(query, None)
        assert result == query
    
    def test_prepare_query_with_memory(self):
        """Test preparing query with memory context."""
        query = "Show tables"
        memory_context = {
            "recent_conversation": ["Previously asked about customers"],
            "user_preferences": {"format": "table"}
        }
        
        result = prepare_query_with_memory(query, memory_context)
        
        assert "User query: Show tables" in result
        assert "Memory context:" in result
        assert "Recent conversation:" in result
        assert "Previously asked about customers" in result
        assert "User preferences:" in result
        assert "format: table" in result
    
    def test_prepare_query_with_empty_formatted_context(self):
        """Test preparing query when memory context formats to empty string."""
        query = "Show tables"
        memory_context = {
            "recent_conversation": [],
            "user_preferences": {},
            "relevant_facts": []
        }
        
        # All sections are empty, so format_memory_context returns empty string
        result = prepare_query_with_memory(query, memory_context)
        
        # Should return original query when formatted context is empty
        assert result == query
    
    def test_prepare_query_integration_with_format_memory_context(self):
        """Test integration with format_memory_context function."""
        query = "Analyze data"
        memory_context = {
            "working_memory": ["Current analysis session"],
            "relevant_facts": ["User prefers visual charts"]
        }
        
        with patch('agentdk.agent.app_utils.format_memory_context', return_value="Formatted context") as mock_format:
            result = prepare_query_with_memory(query, memory_context)
            
            mock_format.assert_called_once_with(memory_context)
            assert result == "User query: Analyze data\\nMemory context: Formatted context"


class TestCreateWorkflowMessages:
    """Test the create_workflow_messages function."""
    
    def test_create_messages_without_memory(self):
        """Test creating messages without memory context."""
        query = "Hello world"
        result = create_workflow_messages(query)
        
        expected = [{"role": "user", "content": "Hello world"}]
        assert result == expected
    
    def test_create_messages_with_none_memory(self):
        """Test creating messages with None memory context."""
        query = "Hello world"
        result = create_workflow_messages(query, None)
        
        expected = [{"role": "user", "content": "Hello world"}]
        assert result == expected
    
    def test_create_messages_with_memory(self):
        """Test creating messages with memory context."""
        query = "Show data"
        memory_context = {"user_preferences": {"format": "json"}}
        
        with patch('agentdk.agent.app_utils.prepare_query_with_memory', return_value="Formatted query") as mock_prepare:
            result = create_workflow_messages(query, memory_context)
            
            mock_prepare.assert_called_once_with(query, memory_context)
            expected = [{"role": "user", "content": "Formatted query"}]
            assert result == expected
    
    def test_create_messages_empty_query(self):
        """Test creating messages with empty query."""
        result = create_workflow_messages("")
        
        expected = [{"role": "user", "content": ""}]
        assert result == expected
    
    def test_create_messages_complex_query(self):
        """Test creating messages with complex query and memory."""
        query = "Analyze sales data for Q3"
        memory_context = {
            "recent_conversation": ["Asked about Q2 data"],
            "user_preferences": {"chart_type": "bar"},
            "relevant_facts": ["User is sales manager"]
        }
        
        # Integration test to verify the full pipeline
        result = create_workflow_messages(query, memory_context)
        
        assert len(result) == 1
        assert result[0]["role"] == "user"
        
        content = result[0]["content"]
        assert "User query: Analyze sales data for Q3" in content
        assert "Memory context:" in content


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple functions."""
    
    def test_full_workflow_memory_integration(self):
        """Test full workflow with memory integration."""
        # Simulate a complete workflow from query to response
        user_query = "Show top customers"
        memory_context = {
            "recent_conversation": ["Asked about sales data"],
            "user_preferences": {"format": "table", "limit": 10}
        }
        
        # 1. Create workflow messages
        messages = create_workflow_messages(user_query, memory_context)
        
        # 2. Simulate LangGraph result
        mock_response_message = Mock()
        mock_response_message.content = "Here are the top 10 customers in table format"
        
        langgraph_result = {"messages": messages + [mock_response_message]}
        
        # 3. Extract response
        final_response = extract_response(langgraph_result)
        
        assert final_response == "Here are the top 10 customers in table format"
        assert messages[0]["content"] != user_query  # Should be enhanced with memory
    
    def test_error_handling_chain(self):
        """Test error handling across function chain."""
        # Test with malformed data through the chain
        
        # 1. Malformed memory context
        malformed_memory = {"invalid_section": "data"}
        formatted = format_memory_context(malformed_memory)
        assert formatted == ""  # Should handle gracefully
        
        # 2. Malformed LangGraph result
        malformed_result = {"not_messages": ["invalid"]}
        
        with patch('agentdk.agent.app_utils.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            response = extract_response(malformed_result)
            
            # Should fallback gracefully
            assert isinstance(response, str)
            mock_logger.warning.assert_called()
    
    def test_supervisor_workflow_with_memory_agents(self):
        """Test supervisor workflow creation with memory-aware agents."""
        # Create mock memory-aware agents
        agent1 = Mock()
        agent1.name = "eda_agent"
        
        agent2 = Mock()
        agent2.name = "research_agent"
        
        mock_model = Mock()
        supervisor_prompt = "You are supervising EDA and research agents"
        
        mock_workflow = Mock()
        mock_app = Mock()
        mock_workflow.compile.return_value = mock_app
        
        with patch('langgraph_supervisor.create_supervisor', return_value=mock_workflow), \
             patch('agentdk.agent.app_utils.get_logger'):
            
            result = create_supervisor_workflow([agent1, agent2], mock_model, supervisor_prompt)
            
            assert result == mock_app
            
            # Verify agents were passed correctly
            import langgraph_supervisor
            langgraph_supervisor.create_supervisor.assert_called_once_with(
                [agent1, agent2], 
                model=mock_model, 
                prompt=supervisor_prompt
            )