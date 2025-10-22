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
        Execute travel planning task

        Steps:
        1. Extract travel parameters from message
        2. Search for flights using Bright Data
        3. Search for hotels using Bright Data
        4. Format results
        """
        try:
            # Get message from input
            message = task.input_data.get('message') or task.input_data.get('text', '')

            if not message.strip():
                return AgentResult(
                    task_id=task.id,
                    output="## Error\n\nPlease provide a travel request message.",
                    actual_cost=0.0,
                    metadata={'error': 'No message provided'},
                    sources=[]
                )

            # Check for Bright Data API key
            if not settings.BRIGHT_DATA_API_KEY:
                return AgentResult(
                    task_id=task.id,
                    output="## Error\n\nBright Data API key not configured. Travel search requires BRIGHT_DATA_API_KEY.",
                    actual_cost=0.0,
                    metadata={'error': 'BRIGHT_DATA_API_KEY not set'},
                    sources=[]
                )

            # Initialize Gemini client
            gemini_client = GeminiClient(api_key=settings.GEMINI_API_KEY)

            # Use async with for proper MCP client lifecycle management
            async with MCPClient(api_key=settings.BRIGHT_DATA_API_KEY) as mcp_client:
                # Log available tools
                available_tools = mcp_client.get_available_tools()
                tool_names = [tool.name for tool in available_tools]
                print(f"[TravelPlanner] MCP tools available: {tool_names}")

                # Create travel search agent
                agent = Agent(
                    name=self.name,
                    role="Travel search specialist that MUST use web scraping tools to find real data",
                    gemini_client=gemini_client,
                    mcp_client=mcp_client,
                    instructions=[
                        "You MUST call the search_engine and scrape_as_markdown tools to get real flight and hotel data",
                        "DO NOT say you cannot provide data - you have the tools to do so",
                        "DO NOT make assumptions or use placeholder data",
                        "",
                        "REQUIRED WORKFLOW:",
                        "1. Call search_engine with query about flights",
                        "2. Call scrape_as_markdown on relevant URLs from search results to get detailed flight data",
                        "3. Call search_engine with query about hotels",
                        "4. Call scrape_as_markdown on relevant URLs from search results to get detailed hotel data",
                        "5. Format the extracted data in a clean, readable format",
                        "",
                        "Extract specific details:",
                        "- Flights: airline, departure/arrival times, duration, price, booking URL",
                        "- Hotels: name, location, rating, price per night, amenities, booking URL"
                    ],
                    add_datetime_to_instructions=True,
                    markdown=True
                )

                # Build direct, action-oriented prompt
                prompt = f"""Search for flights and hotels for this request: "{message}"

YOU MUST:
1. Call search_engine tool with query "flights from [origin] to [destination] [date]"
2. Call scrape_as_markdown tool on booking site URLs from results to get flight details
3. Call search_engine tool with query "hotels in [destination]"
4. Call scrape_as_markdown tool on hotel site URLs from results to get hotel details
5. Present the extracted data

Start by calling the search_engine tool now."""

                # Execute search
                print(f"[TravelPlanner] Starting agent with message: {message[:100]}...")
                response = await agent.arun(prompt)

                return AgentResult(
                    task_id=task.id,
                    output=response.content,
                    actual_cost=self.base_cost,
                    metadata={
                        'message': message[:200],
                        'mcp_enabled': True
                    },
                    sources=[]  # Sources would be embedded in the response
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
