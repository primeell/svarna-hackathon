"""
Project SVARNA — Pipeline Orchestrator
=========================================
Sequential pipeline: Audio → Transcription → Entity Extraction → Economic Analysis
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from src.agents.acoustic_ingestor import AcousticSignalIngestor
from src.agents.macro_strategist import MacroEconomicStrategist
from src.agents.semantic_parser import SemanticDataParser
from src.core.blackboard import Blackboard
from src.core.config_loader import get_agent_config, load_config
from src.utils.logger import setup_logger


class SVARNAPipeline:
    """
    Orchestrates the 3-agent pipeline:
      1. AcousticSignalIngestor — Audio → Text
      2. SemanticDataParser — Text → Structured Data
      3. MacroEconomicStrategist — Data → Economic Intelligence
    """

    def __init__(self, config_path: str = "AgentConfig.yaml"):
        self.config = load_config(config_path)
        system_config = self.config.get("system", {})

        # Setup logger
        setup_logger(
            log_level=system_config.get("log_level", "INFO"),
            log_file=system_config.get("log_file", "logs/svarna.log"),
        )

        # Initialize blackboard
        bb_config = self.config.get("blackboard", {})
        self.blackboard = Blackboard(
            db_path=bb_config.get("path", "data/svarna_blackboard.db")
        )

        # Initialize agents
        self.agents = self._init_agents()
        logger.info(f"SVARNA Pipeline initialized with {len(self.agents)} agents")

    def _init_agents(self) -> list:
        """Create all 3 agents with their configs."""
        agents_config = self.config.get("agents", {})

        agent_list = []

        # Agent 1
        a1_config = agents_config.get("acoustic_signal_ingestor", {})
        agent_list.append(AcousticSignalIngestor(a1_config, self.blackboard))

        # Agent 2
        a2_config = agents_config.get("semantic_data_parser", {})
        agent_list.append(SemanticDataParser(a2_config, self.blackboard))

        # Agent 3
        a3_config = agents_config.get("macro_economic_strategist", {})
        agent_list.append(MacroEconomicStrategist(a3_config, self.blackboard))

        return agent_list

    def run(self, audio_file: Optional[str] = None) -> dict:
        """
        Execute the full pipeline.

        Args:
            audio_file: Path to a farmer's voice note audio file.

        Returns:
            Final pipeline result with all stage outputs.
        """
        logger.info("=" * 60)
        logger.info("SVARNA Pipeline — Starting")
        logger.info("=" * 60)

        results = {}
        current_input: Any = {"audio_file": audio_file} if audio_file else None

        for i, agent in enumerate(self.agents, 1):
            logger.info(f"--- Stage {i}/3: {agent.name} ---")

            try:
                output = agent.run(current_input)
                results[agent.name] = output
                current_input = output  # Feed output as next input

            except Exception as e:
                logger.error(f"Pipeline error at {agent.name}: {e}")
                results[agent.name] = {"status": "failed", "error": str(e)}
                break

        # Summary
        logger.info("=" * 60)
        logger.info("SVARNA Pipeline — Complete")
        logger.info(f"Blackboard stats: {self.blackboard.get_stats()}")
        logger.info("=" * 60)

        return results

    def get_alerts(self) -> list[dict]:
        """Get all economic alerts from the blackboard."""
        return self.blackboard.read("economic_alerts")

    def get_stats(self) -> dict:
        """Get blackboard entry counts."""
        return self.blackboard.get_stats()
