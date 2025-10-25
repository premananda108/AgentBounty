"""MCP Client for Bright Data integration"""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.config import settings


class MCPClient:
    """
    Wrapper for MCP (Model Context Protocol) client to interact with Bright Data via HTTP.
    This class is designed as a singleton, managed by the FastAPI lifespan.
    """

    def __init__(self):
        """
        Initialize MCP client parameters for HTTP transport.
        """
        self.api_key = settings.BRIGHT_DATA_API_KEY
        self.session: Optional[ClientSession] = None
        self.available_tools: List[Dict[str, Any]] = []
        self._http_context = None
        self._session_context = None

    def is_enabled(self) -> bool:
        """Check if the client is configured and enabled."""
        return bool(self.api_key)

    async def startup(self):
        """Starts the MCP client and initializes the session. Called on application startup."""
        if not self.is_enabled():
            print("❌ MCPClient: FATAL - BRIGHT_DATA_API_KEY is not set. MCPClient startup aborted.")
            return

        print("MCPClient: Starting up (StreamableHTTP)...")
        try:
            # --- Start Debug Logging ---
            # Enable detailed logging for httpx to see raw requests/responses
            logging.basicConfig(level=logging.DEBUG)
            httpx_logger = logging.getLogger("httpx")
            httpx_logger.setLevel(logging.DEBUG)
            print("--- HTTPX DEBUG LOGGING ENABLED ---")
            # --- End Debug Logging ---

            self._http_context = streamablehttp_client(
                url="https://mcp.brightdata.com/mcp",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            read_stream, write_stream, _ = await self._http_context.__aenter__()
            print("MCPClient: HTTP client transport started successfully.")

            self._session_context = ClientSession(read_stream, write_stream)
            self.session = await self._session_context.__aenter__()
            print("MCPClient: ClientSession created.")

            await self.session.initialize()
            print("MCPClient: Session initialized.")

            tools_result = await self.session.list_tools()
            self.available_tools = tools_result.tools if hasattr(tools_result, 'tools') else []
            tool_names = [tool.name for tool in self.available_tools]
            print(f"MCPClient: Successfully listed {len(self.available_tools)} tools: {tool_names}")
        except Exception as e:
            print(f"❌ MCPClient: FAILED to start up via HTTP: {e}")
            self.api_key = None # Disable client if startup fails

    async def shutdown(self):
        """Shuts down the MCP client. Called on application shutdown."""
        if not self.is_enabled() or not self._session_context:
            print("MCPClient: Shutdown skipped as client was not running.")
            return

        print("MCPClient: Shutting down (StreamableHTTP)...")
        try:
            await self._session_context.__aexit__(None, None, None)
            await self._http_context.__aexit__(None, None, None)
            print("MCPClient: Shutdown complete.")
        except Exception as e:
            print(f"❌ MCPClient: FAILED to shut down cleanly: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool via MCP"""
        if not self.session:
            raise RuntimeError("MCP session not initialized. Client may be disabled or startup failed.")
        result = await self.session.call_tool(tool_name, arguments)
        return result

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return self.available_tools

    def _clean_schema_for_gemini(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively clean JSON schema for Gemini compatibility"""
        import copy
        if not isinstance(schema, dict):
            return schema
        cleaned = copy.deepcopy(schema)
        fields_to_remove = ['$schema', 'additionalProperties', 'additional_properties']
        for field in fields_to_remove:
            if field in cleaned:
                del cleaned[field]
        if 'type' in cleaned and isinstance(cleaned['type'], str):
            cleaned['type'] = cleaned['type'].upper()
        for key, value in cleaned.items():
            if isinstance(value, dict):
                cleaned[key] = self._clean_schema_for_gemini(value)
            elif isinstance(value, list):
                cleaned[key] = [self._clean_schema_for_gemini(item) if isinstance(item, dict) else item for item in value]
        return cleaned

    def get_tools_for_gemini(self) -> List:
        """Convert MCP tools to Gemini function calling format"""
        from google.genai import types
        gemini_tools = []
        for tool in self.available_tools:
            input_schema = {}
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                input_schema = self._clean_schema_for_gemini(tool.inputSchema)
            func_declaration = types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or f"Tool: {tool.name}",
                parameters=input_schema
            )
            gemini_tools.append(func_declaration)
        return gemini_tools

# --- Singleton Instance ---
mcp_client_instance = MCPClient()

def get_mcp_client() -> MCPClient:
    """FastAPI dependency to get the singleton MCPClient instance."""
    return mcp_client_instance
