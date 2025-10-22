"""MCP Client for Bright Data integration"""
import asyncio
import os
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Wrapper for MCP (Model Context Protocol) client to interact with Bright Data"""

    def __init__(self, api_key: str):
        """
        Initialize MCP client for Bright Data

        Args:
            api_key: Bright Data API key
        """
        self.api_key = api_key

        # Find npx in PATH
        npx_path = self._find_npx()
        if not npx_path:
            raise FileNotFoundError(
                "npx not found. Please install Node.js: "
                "https://nodejs.org/ or https://github.com/nvm-sh/nvm"
            )

        # Construct a PATH that includes the location of node/npx
        system_path = os.environ.get('PATH', '')
        node_path = os.path.dirname(npx_path)  # Get directory of npx
        env_path = f"{node_path}:{system_path}"

        self.server_params = StdioServerParameters(
            command=npx_path,
            args=["-y", "@brightdata/mcp"],
            env={
                "API_TOKEN": api_key,
                "WEB_UNLOCKER_ZONE": "unblocker",
                "BROWSER_ZONE": "scraping_browser",
                "PATH": env_path  # Explicitly provide the PATH
            }
        )

        self.session: Optional[ClientSession] = None
        self.available_tools: List[Dict[str, Any]] = []

    def _find_npx(self) -> Optional[str]:
        """Find npx executable in PATH"""
        import shutil
        return shutil.which("npx")

    async def __aenter__(self):
        """Async context manager entry"""
        print("MCPClient: Entering async context...")
        # Store context managers for proper cleanup
        print(f"MCPClient: Starting stdio_client with command: {' '.join([self.server_params.command] + self.server_params.args)}")
        self._stdio_context = stdio_client(self.server_params)
        self.read, self.write = await self._stdio_context.__aenter__()
        print("MCPClient: Stdio client started successfully.")

        self._session_context = ClientSession(self.read, self.write)
        self.session = await self._session_context.__aenter__()
        print("MCPClient: ClientSession created.")

        await self.session.initialize()
        print("MCPClient: Session initialized.")

        # List available tools
        tools_result = await self.session.list_tools()
        self.available_tools = tools_result.tools if hasattr(tools_result, 'tools') else []
        
        if self.available_tools:
            tool_names = [tool.name for tool in self.available_tools]
            print(f"MCPClient: Successfully listed {len(self.available_tools)} tools: {tool_names}")
        else:
            print("MCPClient: WARNING - No tools listed by the MCP server.")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Clean up in reverse order
        if hasattr(self, '_session_context'):
            await self._session_context.__aexit__(exc_type, exc_val, exc_tb)
        if hasattr(self, '_stdio_context'):
            await self._stdio_context.__aexit__(exc_type, exc_val, exc_tb)

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
            raise RuntimeError("MCP session not initialized. Use 'async with MCPClient(...)'")

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
