"""Gemini API client with function calling support"""
import json
from typing import Any, Dict, List, Optional, Callable
from google import genai
from google.genai import types


class GeminiClient:
    """Wrapper for Google Gemini API with function calling support"""

    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash"):
        """
        Initialize Gemini client

        Args:
            api_key: Google API key
            model_id: Gemini model ID
        """
        self.api_key = api_key
        self.model_id = model_id
        self.client = genai.Client(api_key=api_key)

    async def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        tools: Optional[List] = None,
        tool_executor: Optional[Callable] = None,
        max_iterations: int = 10
    ) -> str:
        """
        Generate content with optional function calling

        Args:
            prompt: User prompt
            system_instruction: System instruction for the model
            tools: List of tools (Python functions or function declarations)
            tool_executor: Async function to execute tool calls
            max_iterations: Maximum number of function calling iterations

        Returns:
            Generated text response
        """
        messages = []
        current_prompt = prompt

        # If tools are provided and tool_executor exists, handle function calling
        if tools and tool_executor:
            # Debug: Log available tools
            print(f"GeminiClient: Configuring {len(tools)} tools for function calling")
            for tool in tools[:3]:  # Log first 3 tools
                print(f"  - {tool.name}: {tool.description[:80]}...")

            # Wrap FunctionDeclarations in Tool object
            tool_object = types.Tool(function_declarations=tools)

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[tool_object]
            )

            for iteration in range(max_iterations):
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=current_prompt,
                    config=config
                )

                # Check if model wants to call a function
                if response.candidates and response.candidates[0].content.parts:
                    parts = response.candidates[0].content.parts

                    # Check for function calls
                    function_calls = [
                        part for part in parts
                        if hasattr(part, 'function_call') and part.function_call
                    ]

                    if function_calls:
                        # Execute all function calls
                        function_responses = []

                        for fc_part in function_calls:
                            fc = fc_part.function_call
                            tool_name = fc.name
                            tool_args = dict(fc.args) if fc.args else {}

                            # Execute the tool
                            result = await tool_executor(tool_name, tool_args)

                            function_responses.append({
                                "name": tool_name,
                                "response": result
                            })

                        # Build next prompt with function results
                        messages.append({
                            "role": "user",
                            "content": current_prompt
                        })
                        messages.append({
                            "role": "model",
                            "function_calls": function_calls
                        })
                        messages.append({
                            "role": "user",
                            "function_responses": function_responses
                        })

                        # Continue the conversation with function results
                        current_prompt = self._build_prompt_with_history(messages)
                        continue

                # No more function calls, extract text from response
                # Handle cases where response includes thought_signature or other non-text parts
                text_parts = [
                    part.text for part in parts
                    if hasattr(part, 'text') and part.text
                ]

                if text_parts:
                    return '\n'.join(text_parts)
                else:
                    # Fallback to response.text which concatenates all text parts
                    return response.text

            # Max iterations reached
            return "Max function calling iterations reached"

        # No tools, simple generation
        else:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=current_prompt,
                config=config
            )

            return response.text

    def _build_prompt_with_history(self, messages: List[Dict]) -> str:
        """Build a prompt string from message history"""
        # For simplicity, concatenate messages
        # In production, you might want to use proper chat format
        prompt_parts = []
        for msg in messages:
            if msg["role"] == "user" and "content" in msg:
                prompt_parts.append(f"User: {msg['content']}")
            elif msg["role"] == "model" and "function_calls" in msg:
                prompt_parts.append("Model requested function calls")
            elif msg["role"] == "user" and "function_responses" in msg:
                responses = msg["function_responses"]
                for resp in responses:
                    prompt_parts.append(f"Function {resp['name']} returned: {resp['response']}")

        return "\n".join(prompt_parts)
