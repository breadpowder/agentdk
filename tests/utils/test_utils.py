"""Tests for utils module."""

import os
import pytest
from unittest.mock import patch, MagicMock

from agentdk.utils.utils import get_llm


class TestGetLLM:
    """Test the get_llm function."""

    @pytest.mark.unit
    @pytest.mark.skip(reason="Requires optional langchain_openai dependency")
    def test_openai_llm_creation_success(self):
        """Test successful OpenAI LLM creation."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('langchain_openai.ChatOpenAI') as mock_openai:
                mock_llm = MagicMock()
                mock_openai.return_value = mock_llm
                
                result = get_llm()
                
                assert result == mock_llm
                mock_openai.assert_called_once_with(model="gpt-4o-mini", temperature=0)

    @pytest.mark.skip(reason="Requires optional langchain_anthropic dependency")
    def test_anthropic_llm_creation_success(self):
        """Test successful Anthropic LLM creation."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}, clear=True):
            with patch('langchain_anthropic.ChatAnthropic') as mock_anthropic:
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
            
            assert "No LLM API key found" in str(exc_info.value)
            assert "OPENAI_API_KEY or ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_no_api_keys_raises_error(self):
        """Test that no API keys raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_llm()
            
            assert "No LLM API key found" in str(exc_info.value)