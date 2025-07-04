"""Tests for utils module."""

import os
import pytest
from unittest.mock import patch, MagicMock

from agentdk.utils.utils import get_llm


class TestGetLLM:
    """Test the get_llm function."""

    def test_openai_llm_creation_success(self):
        """Test successful OpenAI LLM creation."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('agentdk.utils.utils.ChatOpenAI') as mock_openai:
                mock_llm = MagicMock()
                mock_openai.return_value = mock_llm
                
                result = get_llm()
                
                assert result == mock_llm
                mock_openai.assert_called_once_with(model="gpt-4o-mini", temperature=0)

    def test_anthropic_llm_creation_success(self):
        """Test successful Anthropic LLM creation."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}, clear=True):
            with patch('agentdk.utils.utils.ChatAnthropic') as mock_anthropic:
                mock_llm = MagicMock()
                mock_anthropic.return_value = mock_llm
                
                result = get_llm()
                
                assert result == mock_llm
                mock_anthropic.assert_called_once_with(model="claude-3-haiku-20240307", temperature=0)

    def test_no_api_keys_raises_error(self):
        """Test that missing API keys raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_llm()
            
            assert "No LLM available" in str(exc_info.value)
            assert "OPENAI_API_KEY or ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_openai_import_error_tries_anthropic(self):
        """Test that OpenAI import error falls back to Anthropic."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('agentdk.utils.utils.ChatOpenAI', side_effect=ImportError):
                with patch('agentdk.utils.utils.ChatAnthropic') as mock_anthropic:
                    mock_llm = MagicMock()
                    mock_anthropic.return_value = mock_llm
                    
                    result = get_llm()
                    
                    assert result == mock_llm

    def test_all_imports_fail_raises_error(self):
        """Test that all import failures raise ValueError."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('agentdk.utils.utils.ChatOpenAI', side_effect=ImportError):
                with pytest.raises(ValueError) as exc_info:
                    get_llm()
                
                assert "No LLM available" in str(exc_info.value)