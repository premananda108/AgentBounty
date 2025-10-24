"""
AI Travel Planner Agent - Intelligent travel itinerary planning
"""

from typing import Dict, Any
from .base import BaseAgent, AgentTask, AgentResult
from app.core.gemini_client import GeminiClient
from app.core.mcp_client import MCPClient
from app.core.agent import Agent
from app.config import settings


class TravelPlannerAgent(BaseAgent):
    """
    AI Travel Planner Agent that finds flights and hotels

    Uses Bright Data MCP for web scraping and Gemini for planning
    """

    name = "AI Travel Planner"
    description = "Find flights and hotels for your travel plans"
    base_cost = 0.002  # USDC in test network

    async def estimate_cost(self, input_data: Dict) -> float:
        """Estimate cost"""
        return self.base_cost

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data

        Required fields (text mode):
        - message: Natural language travel request

        OR (url mode - not applicable for travel planner):
        - Not used
        """
        if not input_data:
            return False

        # For travel planner, we need either 'message' or 'text'
        if 'message' in input_data and input_data['message'].strip():
            return True
        if 'text' in input_data and input_data['text'].strip():
            return True

        return False

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute travel planning task by using the global MCP client instance.
        """
        from app.core.mcp_client import get_mcp_client

        try:
            message = task.input_data.get('message') or task.input_data.get('text', '')
            if not message.strip():
                raise ValueError("Travel request message is empty.")

            mcp_client = get_mcp_client()
            if not mcp_client.is_enabled():
                raise ConnectionError("Bright Data API key not configured. Travel search is disabled.")

            gemini_client = GeminiClient(api_key=settings.GEMINI_API_KEY)
            
            agent = Agent(
                name=self.name,
                role="Travel search specialist that MUST use web scraping tools to find real data",
                gemini_client=gemini_client,
                mcp_client=mcp_client,
                instructions=[
                    "You MUST call the search_engine and scrape_as_markdown tools to get real flight and hotel data.",
                    "DO NOT make up information. If you cannot find information, state that clearly.",
                    "REQUIRED WORKFLOW:",
                    "1. Call search_engine for flights.",
                    "2. Call scrape_as_markdown on relevant URLs to get flight details.",
                    "3. Call search_engine for hotels.",
                    "4. Call scrape_as_markdown on relevant URLs to get hotel details.",
                    "5. Format the extracted data clearly."
                ],
                add_datetime_to_instructions=True,
                markdown=True
            )

            prompt = f"""Search for flights and hotels for this request: "{message}"

You MUST use your tools to find real-time information. Start by calling the search_engine tool now."""

            print(f"[TravelPlanner] Starting agent with message: {message[:100]}...")
            response = await agent.arun(prompt)

            return AgentResult(
                task_id=task.id,
                output=response.content,
                actual_cost=self.base_cost,
                metadata={'message': message[:200], 'mcp_enabled': True},
                sources=[]
            )

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return AgentResult(
                task_id=task.id,
                output=f"## Error\n\nFailed to search for travel options: {str(e)}\n\n```\n{error_details}\n```",
                actual_cost=0.0,
                metadata={'error': str(e)},
                sources=[]
            )
