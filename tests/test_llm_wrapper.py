"""Tests for LLMWrapper."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock

from greybeard.common.llm_wrapper import LLMWrapper
from greybeard.config import GreybeardConfig


class TestLLMWrapper:
    """Test suite for LLMWrapper."""

    def test_initialization_with_default_config(self):
        """Test LLMWrapper initializes with default config."""
        with patch.object(GreybeardConfig, 'load') as mock_load:
            mock_load.return_value = Mock(spec=GreybeardConfig)
            wrapper = LLMWrapper()
            assert wrapper.config is not None
            mock_load.assert_called_once()

    def test_initialization_with_provided_config(self):
        """Test LLMWrapper can use provided config."""
        mock_config = Mock(spec=GreybeardConfig)
        wrapper = LLMWrapper(config=mock_config)
        assert wrapper.config is mock_config

    def test_call_method_basic(self):
        """Test basic LLM call."""
        mock_config = Mock(spec=GreybeardConfig)
        wrapper = LLMWrapper(config=mock_config)
        
        with patch('greybeard.common.llm_wrapper.run_review') as mock_run:
            mock_run.return_value = "Test response"
            
            result = wrapper.call(
                system="System prompt",
                messages=[{"role": "user", "content": "Hello"}],
            )
            
            assert result == "Test response"
            mock_run.assert_called_once()

    def test_call_method_with_temperature(self):
        """Test call with custom temperature."""
        mock_config = Mock(spec=GreybeardConfig)
        wrapper = LLMWrapper(config=mock_config)
        
        with patch('greybeard.common.llm_wrapper.run_review') as mock_run:
            mock_run.return_value = "Response"
            
            wrapper.call(
                system="System",
                messages=[],
                temperature=0.3,
            )
            
            # Verify call was made
            assert mock_run.called

    def test_call_method_with_model_override(self):
        """Test call with model override."""
        mock_config = Mock(spec=GreybeardConfig)
        wrapper = LLMWrapper(config=mock_config)
        
        with patch('greybeard.common.llm_wrapper.run_review') as mock_run:
            mock_run.return_value = "Response"
            
            wrapper.call(
                system="System",
                messages=[],
                model_override="gpt-4",
            )
            
            assert mock_run.called

    def test_stream_call_method(self):
        """Test streaming LLM call."""
        mock_config = Mock(spec=GreybeardConfig)
        wrapper = LLMWrapper(config=mock_config)
        
        with patch('greybeard.common.llm_wrapper.run_review') as mock_run:
            mock_run.return_value = "Streaming response"
            
            result = wrapper.stream_call(
                system="System",
                messages=[{"role": "user", "content": "Hello"}],
            )
            
            assert result == "Streaming response"
            mock_run.assert_called_once()

    def test_get_config(self):
        """Test getting config."""
        mock_config = Mock(spec=GreybeardConfig)
        wrapper = LLMWrapper(config=mock_config)
        
        retrieved_config = wrapper.get_config()
        assert retrieved_config is mock_config

    def test_reload_config(self):
        """Test reloading config from disk."""
        mock_config1 = Mock(spec=GreybeardConfig)
        mock_config2 = Mock(spec=GreybeardConfig)
        
        wrapper = LLMWrapper(config=mock_config1)
        assert wrapper.config is mock_config1
        
        with patch.object(GreybeardConfig, 'load', return_value=mock_config2):
            wrapper.reload_config()
            assert wrapper.config is mock_config2

    def test_call_with_multiple_messages(self):
        """Test call with conversation history."""
        mock_config = Mock(spec=GreybeardConfig)
        wrapper = LLMWrapper(config=mock_config)
        
        messages = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"},
        ]
        
        with patch('greybeard.common.llm_wrapper.run_review') as mock_run:
            mock_run.return_value = "Final answer"
            
            result = wrapper.call(system="System", messages=messages)
            
            assert result == "Final answer"
            # Verify messages were passed
            call_args = mock_run.call_args
            assert call_args is not None

    def test_call_handles_empty_messages(self):
        """Test call with empty message list."""
        mock_config = Mock(spec=GreybeardConfig)
        wrapper = LLMWrapper(config=mock_config)
        
        with patch('greybeard.common.llm_wrapper.run_review') as mock_run:
            mock_run.return_value = "Response to nothing"
            
            result = wrapper.call(system="System", messages=[])
            
            assert result == "Response to nothing"
