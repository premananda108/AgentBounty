"""
Scraper Agent - Web scraping agent for extracting data from URLs
"""

from typing import Dict, Any
from .base import BaseAgent, AgentTask, AgentResult
from app.config import settings
from app.core.mcp_client import MCPClient
import asyncio


class ScraperAgent(BaseAgent):
    """
    Web scraping agent that extracts data from provided URLs

    Uses Bright Data SDK for web scraping with automatic
    unblocking and CAPTCHA solving.
    """

    name = "Scraper Agent"
    description = "Web scraping agent for extracting data from URLs"
    base_cost = 0.0005  # USDC in test network

    async def estimate_cost(self, input_data: Dict) -> float:
        """Estimate cost - fixed for now"""
        return self.base_cost

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data

        Required fields:
        - url: URL to scrape
        """
        if not input_data:
            return False

        if 'url' not in input_data or not input_data['url'].strip():
            return False

        return True

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute web scraping task using Bright Data HTTP API
        """
        url = task.input_data['url'].strip()

        try:
            # Check if Bright Data API key is configured
            if not settings.BRIGHT_DATA_API_KEY:
                return self._create_error_result(
                    task.id,
                    url,
                    "Bright Data API key not configured. Please set BRIGHT_DATA_API_KEY in environment variables."
                )

            # Use simple HTTP API approach
            scraped_data = await self._scrape_url_http(url)

            # Format the output
            output = self._format_output(url, scraped_data)

            return AgentResult(
                task_id=task.id,
                output=output,
                actual_cost=self.base_cost,
                metadata={
                    'url': url,
                    'status': 'success',
                    'scraped_at': scraped_data.get('timestamp'),
                    'content_length': len(scraped_data.get('content', ''))
                },
                sources=[url]
            )

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return self._create_error_result(task.id, url, str(e), error_details)

    async def _scrape_url_http(self, url: str) -> Dict[str, Any]:
        """
        Scrape URL using Bright Data SDK (properly in async)

        Args:
            url: URL to scrape

        Returns:
            Dict with scraped data including content, metadata, etc.
        """
        from datetime import datetime

        try:
            print(f"[Scraper] Scraping URL: {url}")

            # Import and use SDK properly
            from brightdata import bdclient

            # Run in thread pool to avoid blocking
            def scrape_sync():
                # Initialize exactly as in working test
                client = bdclient(api_token=settings.BRIGHT_DATA_API_KEY)
                # Call exactly as in working test - no extra parameters
                result = client.scrape(url=url)
                return result

            # Execute in thread pool
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, scrape_sync)

            print(f"[Scraper] Response type: {type(content)}")
            print(f"[Scraper] Response length: {len(content) if isinstance(content, str) else 'N/A'}")

            # If content is empty, log the raw response
            if not content or len(content) == 0:
                print(f"[Scraper] WARNING: Empty content received")
                print(f"[Scraper] Raw response: {content}")

            return {
                'content': content if isinstance(content, str) else str(content),
                'timestamp': datetime.utcnow().isoformat(),
                'url': url
            }

        except Exception as e:
            print(f"[Scraper] Exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to scrape URL: {str(e)}")

    async def _scrape_url_mcp(self, url: str, mcp_client: MCPClient) -> Dict[str, Any]:
        """
        Scrape URL using Bright Data MCP

        Args:
            url: URL to scrape
            mcp_client: MCP client instance

        Returns:
            Dict with scraped data including content, metadata, etc.
        """
        from datetime import datetime

        try:
            print(f"[Scraper] Using MCP to scrape: {url}")

            # Call scrape_as_markdown tool via MCP
            result = await mcp_client.call_tool(
                tool_name="scrape_as_markdown",
                arguments={"url": url}
            )

            print(f"[Scraper MCP] Result type: {type(result)}")
            print(f"[Scraper MCP] Result: {result}")

            # Extract content from MCP result
            content = ""
            if hasattr(result, 'content'):
                # MCP returns result with .content attribute
                if isinstance(result.content, list) and len(result.content) > 0:
                    first_item = result.content[0]
                    if hasattr(first_item, 'text'):
                        content = first_item.text
                    else:
                        content = str(first_item)
                else:
                    content = str(result.content)
            else:
                content = str(result)

            print(f"[Scraper MCP] Extracted content length: {len(content)}")

            return {
                'content': content,
                'timestamp': datetime.utcnow().isoformat(),
                'url': url
            }

        except Exception as e:
            print(f"[Scraper MCP] Exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to scrape URL via MCP: {str(e)}")

    async def _scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape URL using Bright Data SDK

        Args:
            url: URL to scrape

        Returns:
            Dict with scraped data including content, metadata, etc.
        """
        from datetime import datetime

        try:
            # Import Bright Data SDK
            from brightdata import bdclient

            print(f"[Scraper] Initializing client with API key: {settings.BRIGHT_DATA_API_KEY[:10]}...")
            # Initialize client
            client = bdclient(api_token=settings.BRIGHT_DATA_API_KEY)
            print(f"[Scraper] Client initialized successfully")

            print(f"[Scraper] Starting scrape for URL: {url}")
            # Run scraping in executor since bdclient is synchronous
            loop = asyncio.get_event_loop()

            def scrape_sync():
                print(f"[Scraper] Inside executor, calling client.scrape...")
                result = client.scrape(
                    url,
                    response_format='raw',  # Get raw HTML
                    timeout=30
                )
                print(f"[Scraper] Scrape returned, type: {type(result)}, length: {len(result) if isinstance(result, str) else 'N/A'}")
                return result

            result = await loop.run_in_executor(None, scrape_sync)
            print(f"[Scraper] Executor finished")

            # Debug: log the raw result
            print(f"[Scraper] Raw result type: {type(result)}")
            print(f"[Scraper] Raw result length: {len(str(result))}")
            if isinstance(result, str):
                print(f"[Scraper] Raw result preview: {result[:500]}...")
            else:
                print(f"[Scraper] Raw result: {result}")

            # Extract content from result
            # With response_format='raw', result should be a string with HTML
            if isinstance(result, str):
                print(f"[Scraper] Result is string with length: {len(result)}")
                content = result
            elif isinstance(result, list) and len(result) > 0:
                print(f"[Scraper] Result is list with {len(result)} items")
                # Handle list response
                first_result = result[0]
                print(f"[Scraper] First result type: {type(first_result)}")

                if isinstance(first_result, dict):
                    # Try different possible keys
                    content = (
                        first_result.get('content') or
                        first_result.get('markdown') or
                        first_result.get('text') or
                        first_result.get('html') or
                        str(first_result)
                    )
                    print(f"[Scraper] Extracted from dict, length: {len(content)}")
                else:
                    content = str(first_result)
                    print(f"[Scraper] Converted to string, length: {len(content)}")
            elif isinstance(result, dict):
                print(f"[Scraper] Result is dict with keys: {result.keys()}")
                # Try different possible keys
                content = (
                    result.get('content') or
                    result.get('markdown') or
                    result.get('text') or
                    result.get('html') or
                    str(result)
                )
                print(f"[Scraper] Extracted from dict, length: {len(content)}")
            else:
                print(f"[Scraper] Result is unknown type, converting to string")
                content = str(result)

            print(f"[Scraper] Final content length: {len(content)}")

            return {
                'content': content,
                'timestamp': datetime.utcnow().isoformat(),
                'url': url
            }

        except ImportError as e:
            print(f"[Scraper] ImportError: {e}")
            raise Exception("Bright Data SDK not installed. Run: pip install brightdata-sdk")
        except Exception as e:
            print(f"[Scraper] Exception during scraping: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to scrape URL: {str(e)}")

    def _format_output(self, url: str, scraped_data: Dict[str, Any]) -> str:
        """Format scraped data into markdown output"""
        content = scraped_data.get('content', '')
        timestamp = scraped_data.get('timestamp', 'N/A')

        output = f"""# Web Scraping Result

## Target URL
{url}

## Scraping Status
✅ Successfully scraped

## Scraped At
{timestamp}

## Content Length
{len(content)} characters

---

## Extracted Content

{content}

---

*Scraped using Bright Data Web Scraper*
"""
        return output

    def _create_error_result(
        self,
        task_id: str,
        url: str,
        error_message: str,
        error_details: str = None
    ) -> AgentResult:
        """Create error result"""
        output = f"""# Web Scraping Result

## Target URL
{url}

## Scraping Status
❌ Failed

## Error
{error_message}
"""

        if error_details:
            output += f"""
## Error Details
```
{error_details}
```
"""

        return AgentResult(
            task_id=task_id,
            output=output,
            actual_cost=0.0,  # No cost for failed tasks
            metadata={
                'url': url,
                'status': 'error',
                'error': error_message
            },
            sources=[url]
        )
