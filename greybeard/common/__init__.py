"""Shared agent framework and utilities for Greybeard.

This module contains the foundational classes and utilities that all
Greybeard agents inherit from and use.
"""

from __future__ import annotations

from .agent import BaseAgent
from .llm_wrapper import LLMWrapper
from .research import ResearchCapability
from .interview import InterviewCapability
from .document import DocumentationGenerator

__all__ = [
    "BaseAgent",
    "LLMWrapper",
    "ResearchCapability",
    "InterviewCapability",
    "DocumentationGenerator",
]
