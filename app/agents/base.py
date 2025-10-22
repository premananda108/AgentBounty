"""Base agent classes and interfaces"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class AgentTask:
    """Task input for agent execution"""
    id: str
    user_id: str
    agent_type: str
    input_data: Dict
    estimated_cost: float


@dataclass
class AgentResult:
    """Result from agent execution"""
    task_id: str
    output: str
    actual_cost: float
    metadata: Dict
    sources: Optional[List[str]] = None


class BaseAgent(ABC):
    """Base class for all AgentBounty agents"""

    name: str = "Base Agent"
    description: str = "Base agent class"
    base_cost: float = 0.0

    @abstractmethod
    async def estimate_cost(self, input_data: Dict) -> float:
        """
        Estimate task cost before execution

        Args:
            input_data: Task input data

        Returns:
            Estimated cost in USD
        """
        pass

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute task and return result

        Args:
            task: AgentTask with all required data

        Returns:
            AgentResult with output and metadata
        """
        pass

    @abstractmethod
    async def validate_input(self, input_data: Dict) -> bool:
        """
        Validate input before execution

        Args:
            input_data: Task input data

        Returns:
            True if valid, False otherwise
        """
        pass

    def to_dict(self) -> Dict:
        """Convert agent info to dict"""
        return {
            "name": self.name,
            "description": self.description,
            "base_cost": self.base_cost
        }
