"""
MCP Server for AgentBounty

Exposes AgentBounty agents as MCP tools.
"""

import functools
from mcp.server.fastmcp import FastMCP, Context
from app.config import settings
from app.services.task_service import get_task_service, TaskService
from app.agents.registry import get_agent

# --- Constants ---
MCP_USER_ID = "mcp-service-user"

# --- MCP Server Setup ---
mcp_server = FastMCP(
    name="AgentBountyMCP",
    instructions="""This server provides access to the AgentBounty AI agents.
You can use the available tools to perform tasks like fact-checking and travel planning."""
)

# --- Authentication ---
def require_api_key(func):
    """Decorator to protect tools with API key authentication."""
    @functools.wraps(func)
    async def wrapper(ctx: Context, *args, **kwargs):
        api_key = ctx.get_header("X-API-Key")
        if not api_key or api_key != settings.MCP_SERVICE_TOKEN:
            raise PermissionError("Invalid or missing API key.")
        return await func(ctx, *args, **kwargs)
    return wrapper

# --- Tool Implementations ---
@mcp_server.tool()
@require_api_key
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

    task_service = get_task_service()
    task = await task_service.create_task(
        user_id=MCP_USER_ID,
        agent_type="factcheck",
        input_data=input_data
    )

    result = await task_service.execute_task(task['id'], MCP_USER_ID)
    return result['output_data']['output']


@mcp_server.tool()
@require_api_key
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

    task_service = get_task_service()
    task = await task_service.create_task(
        user_id=MCP_USER_ID,
        agent_type="travel_planner",
        input_data=input_data
    )

    result = await task_service.execute_task(task['id'], MCP_USER_ID)
    return result['output_data']['output']

# Expose the server's router for inclusion in the main app
_mcp_app = mcp_server.streamable_http_app()
mcp_router = _mcp_app.router
