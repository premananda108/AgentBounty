"""MCP Client for Bright Data integration"""
import asyncio
import os
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.config import settings


class MCPClient:
    """
    Wrapper for MCP (Model Context Protocol) client to interact with Bright Data.
    This class is designed as a singleton, managed by the FastAPI lifespan.
    """

    def __init__(self):
        """
        Initialize MCP client parameters. Does not start the client.
        """
        self.api_key = settings.BRIGHT_DATA_API_KEY
        self.server_params = None
        self.session: Optional[ClientSession] = None
        self.available_tools: List[Dict[str, Any]] = []
        self._stdio_context = None
        self._session_context = None

        if self.api_key:
            npx_path = self._find_npx()
            if not npx_path:
                print("⚠️ WARNING: npx not found. MCPClient for Bright Data will be disabled.")
                return

            system_path = os.environ.get('PATH', '')
            node_path = os.path.dirname(npx_path)
            env_path = f"{node_path}:{system_path}"

            self.server_params = StdioServerParameters(
                command=npx_path,
                args=["-y", "@brightdata/mcp"],
                env={
                    "API_TOKEN": self.api_key,
                    "WEB_UNLOCKER_ZONE": "unblocker",
                    "BROWSER_ZONE": "scraping_browser",
                    "PATH": env_path
                }
            )
        else:
            print("ℹ️ INFO: BRIGHT_DATA_API_KEY not set. MCPClient will be disabled.")

    def is_enabled(self) -> bool:
        """Check if the client is configured and enabled."""
        return self.server_params is not None

    async def startup(self):
        """Starts the MCP client and initializes the session. Called on application startup."""
        if not self.is_enabled():
            print("MCPClient: Startup skipped as client is disabled.")
            return

        print("MCPClient: Starting up...")
        try:
            self._stdio_context = stdio_client(self.server_params)
            self.read, self.write = await self._stdio_context.__aenter__()
            print("MCPClient: Stdio client transport started successfully.")

            self._session_context = ClientSession(self.read, self.write)
            self.session = await self._session_context.__aenter__()
            print("MCPClient: ClientSession created.")

            await self.session.initialize()
            print("MCPClient: Session initialized.")

            tools_result = await self.session.list_tools()
            self.available_tools = tools_result.tools if hasattr(tools_result, 'tools') else []
            tool_names = [tool.name for tool in self.available_tools]
            print(f"MCPClient: Successfully listed {len(self.available_tools)} tools: {tool_names}")
        except Exception as e:
            print(f"❌ MCPClient: FAILED to start up: {e}")
            self.server_params = None # Disable client if startup fails

    async def shutdown(self):
        """Shuts down the MCP client. Called on application shutdown."""
        if not self.is_enabled() or not self._session_context:
            print("MCPClient: Shutdown skipped as client was not running.")
            return

        print("MCPClient: Shutting down...")
        try:
            await self._session_context.__aexit__(None, None, None)
            await self._stdio_context.__aexit__(None, None, None)
            print("MCPClient: Shutdown complete.")
        except Exception as e:
            print(f"❌ MCPClient: FAILED to shut down cleanly: {e}")

    def _find_npx(self) -> Optional[str]:
        """Find npx executable in PATH"""
        import shutil
        return shutil.which("npx")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool via MCP

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        if not self.session:
            raise RuntimeError("MCP session not initialized. Client may be disabled or startup failed.")

        result = await self.session.call_tool(tool_name, arguments)
        return result

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return self.available_tools

    def _clean_schema_for_gemini(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively clean JSON schema for Gemini compatibility
        Removes fields that Gemini doesn't accept and converts type to uppercase
        """
        import copy

        if not isinstance(schema, dict):
            return schema

        cleaned = copy.deepcopy(schema)

        # Remove fields Gemini doesn't accept
        fields_to_remove = ['$schema', 'additionalProperties', 'additional_properties']
        for field in fields_to_remove:
            if field in cleaned:
                del cleaned[field]
        
        # Gemini's FunctionDeclaration expects uppercase type names.
        if 'type' in cleaned and isinstance(cleaned['type'], str):
            cleaned['type'] = cleaned['type'].upper()

        # Recursively clean nested objects
        for key, value in cleaned.items():
            if isinstance(value, dict):
                cleaned[key] = self._clean_schema_for_gemini(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    self._clean_schema_for_gemini(item) if isinstance(item, dict) else item
                    for item in value
                ]

        return cleaned

    def get_tools_for_gemini(self) -> List:
        """
        Convert MCP tools to Gemini function calling format

        Returns:
            List of FunctionDeclaration objects for Gemini
        """
        from google.genai import types

        gemini_tools = []

        for tool in self.available_tools:
            # Get input schema and clean it for Gemini
            input_schema = {}
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                input_schema = self._clean_schema_for_gemini(tool.inputSchema)

            # Create FunctionDeclaration for Gemini
            func_declaration = types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or f"Tool: {tool.name}",
                parameters=input_schema
            )

            gemini_tools.append(func_declaration)

        return gemini_tools

# --- Singleton Instance ---
# This global instance will be managed by the FastAPI lifespan.
mcp_client_instance = MCPClient()

def get_mcp_client() -> MCPClient:
    """FastAPI dependency to get the singleton MCPClient instance."""
    return mcp_client_instance
