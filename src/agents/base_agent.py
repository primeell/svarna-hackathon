"""
Project SVARNA — Base Agent
==============================
Abstract base class defining the lifecycle for all pipeline agents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from src.core.blackboard import Blackboard


class BaseAgent(ABC):
    """
    Abstract agent with a standardized lifecycle:
      1. initialize() — One-time setup (load models, connect)
      2. process() — Main task execution
      3. validate() — Output quality check
      4. write_output() — Push results to the blackboard
    """

    def __init__(self, name: str, config: dict, blackboard: Blackboard):
        self.name = name
        self.config = config
        self.blackboard = blackboard
        self._initialized = False

    def run(self, input_data: Any = None) -> dict:
        """Execute the full agent lifecycle."""
        logger.info(f"[{self.name}] Starting run...")

        if not self._initialized:
            self.initialize()
            self._initialized = True

        # Process
        result = self.process(input_data)
        logger.info(f"[{self.name}] Processing complete")

        # Validate
        is_valid, issues = self.validate(result)
        if not is_valid:
            logger.warning(f"[{self.name}] Validation issues: {issues}")
            result["_validation_issues"] = issues
            result["_status"] = "clarification_needed"
        else:
            result["_status"] = "completed"

        # Write to blackboard
        self.write_output(result)
        logger.info(f"[{self.name}] Output written to blackboard")

        return result

    @abstractmethod
    def initialize(self) -> None:
        """One-time setup (load models, verify hardware, etc.)."""
        ...

    @abstractmethod
    def process(self, input_data: Any) -> dict:
        """Main processing logic. Returns a result dictionary."""
        ...

    @abstractmethod
    def validate(self, result: dict) -> tuple[bool, list[str]]:
        """Validate output quality. Returns (is_valid, list_of_issues)."""
        ...

    @abstractmethod
    def write_output(self, result: dict) -> None:
        """Write validated result to the blackboard."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name!r})>"
