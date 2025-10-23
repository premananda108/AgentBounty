"""
Standalone MCP Server for AgentBounty
"""
import sys
from mcp.server.fastmcp import FastMCP, Context
from app.agents.registry import get_agent

# --- MCP Server Setup ---
mcp_server = FastMCP(
    name="AgentBountyMCP",
    instructions="""This server provides access to the AgentBounty AI agents.
You can use the available tools to perform tasks like fact-checking and travel planning."""
)

# --- Tool Implementations ---
@mcp_server.tool()
async def fact_check(ctx: Context, url: str = None, text: str = None) -> str:
    """
    Performs a fact-check on a given URL or text.

    Args:
        url: The URL of the social media post to fact-check.
        text: The text content to fact-check.

    Returns:
        A markdown-formatted string with the fact-check results.
    """
    if not url and not text:
        raise ValueError("Either 'url' or 'text' must be provided.")

    input_data = {"mode": "url" if url else "text", "url": url, "text": text}

    agent = get_agent("factcheck")
    # Assuming agent.run returns a dict like {'output': '...'}
    result = await agent.run(input_data)
    return result['output']


@mcp_server.tool()
async def plan_travel(ctx: Context, message: str) -> str:
    """
    Creates a travel plan based on a natural language message.

    Args:
        message: A message describing the travel plans (e.g., "I want to fly from New York to London next week").

    Returns:
        A markdown-formatted string with the travel plan.
    """
    if not message:
        raise ValueError("'message' must be provided.")

    input_data = {"message": message}

    agent = get_agent("travel_planner")
    result = await agent.run(input_data)
    return result['output']

# --- Server Runner ---
if __name__ == "__main__":
    # Можно указать порт из аргументов командной строки
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001

    print(f"🚀 Starting Standalone AgentBounty MCP server on port {port}...")
    print(f"📍 URL: http://localhost:{port}/mcp")
    print("📝 Press Ctrl+C to stop")

    # Настройка порта
    mcp_server.settings.port = port

    # Запуск
    mcp_server.run(transport="streamable-http")
