"""Simple Agent class for LLM-based agents"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from .gemini_client import GeminiClient
from .mcp_client import MCPClient


@dataclass
class AgentResponse:
    """Response from agent execution"""
    content: str
    metadata: Optional[Dict[str, Any]] = None


class Agent:
    """Simple agent with LLM and optional tool support"""

    def __init__(
        self,
        name: str,
        role: str,
        gemini_client: GeminiClient,
        instructions: List[str],
        mcp_client: Optional[MCPClient] = None,
        add_datetime_to_instructions: bool = True,
        markdown: bool = True
    ):
        """
        Initialize Agent

        Args:
            name: Agent name
            role: Agent role description
            gemini_client: Gemini API client
            instructions: List of instruction strings
            mcp_client: Optional MCP client for tool access
            add_datetime_to_instructions: Add current datetime to instructions
            markdown: Format output as markdown
        """
        self.name = name
        self.role = role
        self.gemini_client = gemini_client
        self.instructions = instructions
        self.mcp_client = mcp_client
        self.add_datetime_to_instructions = add_datetime_to_instructions
        self.markdown = markdown

    def _build_system_instruction(self) -> str:
        """Build system instruction from role and instructions"""
        instruction_parts = [
            f"You are {self.name}.",
            f"Your role: {self.role}",
            "",
            "Instructions:"
        ]

        for idx, instruction in enumerate(self.instructions, 1):
            instruction_parts.append(f"{idx}. {instruction}")

        if self.add_datetime_to_instructions:
            from datetime import datetime
            instruction_parts.append(f"\nCurrent date and time: {datetime.now().isoformat()}")

        if self.markdown:
            instruction_parts.append("\nFormat your response in Markdown.")

        return "\n".join(instruction_parts)

    async def arun(self, prompt: str) -> AgentResponse:
        """
        Run agent asynchronously

        Args:
            prompt: User prompt

        Returns:
            AgentResponse with generated content
        """
        system_instruction = self._build_system_instruction()

        # If MCP client is available, use tools
        if self.mcp_client:
            from google.genai.types import FunctionResponse

            tools = self.mcp_client.get_tools_for_gemini()

            async def tool_executor(tool_name: str, arguments: Dict[str, Any]) -> Any:
                """Execute tool via MCP client and wrap for Gemini"""
                print(f"Agent: Executing tool '{tool_name}' with args: {arguments}")
                result = await self.mcp_client.call_tool(tool_name, arguments)
                
                # Extract content from MCP result
                content_to_return = ""
                if hasattr(result, 'content'):
                    content_to_return = result.content
                else:
                    content_to_return = str(result)
                
                print(f"Agent: Tool '{tool_name}' executed, returning content of length {len(content_to_return)}.")

                # Wrap the result in the format Gemini expects
                return FunctionResponse(
                    name=tool_name,
                    response={'content': content_to_return}
                )

            content = await self.gemini_client.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                tools=tools,
                tool_executor=tool_executor
            )
        else:
            # No tools, simple generation
            content = await self.gemini_client.generate_content(
                prompt=prompt,
                system_instruction=system_instruction
            )

        return AgentResponse(content=content)
