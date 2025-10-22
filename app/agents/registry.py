"""Agent registry - central place to register all agents"""
from typing import Dict
from app.agents.base import BaseAgent
from app.agents.factcheck import FactCheckAgent
from app.agents.ai_travel_planner import TravelPlannerAgent


# Agent registry
AGENT_REGISTRY: Dict[str, BaseAgent] = {
    'factcheck': FactCheckAgent(),
    'ai-travel-planner': TravelPlannerAgent(),
}


def get_agent(agent_type: str) -> BaseAgent:
    """
    Get agent by type

    Args:
        agent_type: Agent type key

    Returns:
        Agent instance

    Raises:
        KeyError: If agent type not found
    """
    if agent_type not in AGENT_REGISTRY:
        raise KeyError(f"Agent type '{agent_type}' not found. Available: {list(AGENT_REGISTRY.keys())}")

    return AGENT_REGISTRY[agent_type]


def list_agents() -> Dict[str, Dict]:
    """
    List all available agents

    Returns:
        Dict with agent_type -> agent_info mapping
    """
    return {
        agent_type: agent.to_dict()
        for agent_type, agent in AGENT_REGISTRY.items()
    }
