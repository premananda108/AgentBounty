"""
FactCheck Agent - Multi-stage fact-checking agent
Based on FactFlux architecture, adapted for AgentBounty
"""

from typing import Dict, Any, Optional
from .base import BaseAgent, AgentTask, AgentResult
from app.core.gemini_client import GeminiClient
from app.core.mcp_client import MCPClient
from app.core.agent import Agent
from app.config import settings


class FactCheckAgent(BaseAgent):
    """
    Fact-checking agent that verifies claims from social media posts

    Uses a multi-stage pipeline:
    1. Content Extraction - Extract post content using MCP web scraping
    2. Claim Identification - Identify verifiable claims using Gemini
    3. Cross-Reference - Verify claims against sources using MCP search
    4. Verdict Synthesis - Provide final verdict using Gemini
    """

    name = "FactCheck Agent"
    description = "Multi-stage fact-checking for social media posts and claims"
    base_cost = 0.001  # USDC in test network

    async def estimate_cost(self, input_data: Dict) -> float:
        """Estimate cost - fixed for now"""
        return self.base_cost

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data

        Required fields:
        - url: Social media post URL OR text content
        - mode: 'url' or 'text'
        """
        if not input_data:
            return False

        mode = input_data.get('mode', 'text')

        if mode == 'url':
            if 'url' not in input_data or not input_data['url'].strip():
                return False
        elif mode == 'text':
            if 'text' not in input_data or not input_data['text'].strip():
                return False
        else:
            return False

        return True

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute fact-checking pipeline with real Gemini + MCP integration
        """
        gemini_client = GeminiClient(api_key=settings.GEMINI_API_KEY)
        mode = task.input_data.get('mode', 'text')

        # Use async with for proper MCP client lifecycle management
        async with MCPClient(api_key=settings.BRIGHT_DATA_API_KEY) as mcp_client:
            if mode == 'url':
                url = task.input_data['url'].strip()
                result_dict = await self._factcheck_url(url, gemini_client, mcp_client)
            else:
                text = task.input_data['text'].strip()
                result_dict = await self._factcheck_text(text, gemini_client, mcp_client)

        # Convert to AgentResult
        return AgentResult(
            task_id=task.id,
            output=result_dict['content'],
            actual_cost=self.base_cost,
            metadata={
                'verdict': result_dict.get('verdict'),
                'confidence': result_dict.get('confidence'),
                'claims': result_dict.get('claims', []),
            },
            sources=result_dict.get('sources', [])
        )

    async def _factcheck_url(
        self,
        url: str,
        gemini_client: GeminiClient,
        mcp_client: Optional[MCPClient]
    ) -> Dict[str, Any]:
        """Fact-check a social media URL using 4-stage pipeline"""
        try:
            print(f"FactCheckAgent: Starting URL fact-check for: {url}")
            # Stage 1: Content Extraction (requires MCP)
            if not mcp_client:
                print("FactCheckAgent: ERROR - MCPClient not available.")
                return {
                    'content': "## Error\n\nURL fact-checking requires Bright Data integration. Please use text mode or configure BRIGHT_DATA_API_KEY.",
                    'verdict': 'ERROR',
                    'confidence': 0,
                    'claims': [],
                    'sources': []
                }

            print("FactCheckAgent: [Stage 1/4] Starting Content Extraction...")
            extraction_agent = self._create_content_extractor(gemini_client, mcp_client)
            extraction_response = await extraction_agent.arun(
                f"Extract data from this social media post: {url}\n\nYou MUST call the appropriate tool (web_data_tiktok_posts for TikTok, or scrape_as_markdown for other platforms). Start now."
            )
            extracted_content = extraction_response.content
            print("FactCheckAgent: [Stage 1/4] Content Extraction COMPLETE.")

            # Stage 2: Claim Identification
            print("FactCheckAgent: [Stage 2/4] Starting Claim Identification...")
            claim_agent = self._create_claim_identifier(gemini_client)
            claim_response = await claim_agent.arun(
                f"Analyze the following extracted content and identify all verifiable factual claims:\n\n{extracted_content}"
            )
            claims_text = claim_response.content
            print("FactCheckAgent: [Stage 2/4] Claim Identification COMPLETE.")

            # Stage 3: Cross-Reference (requires MCP for web search)
            print("FactCheckAgent: [Stage 3/4] Starting Cross-Reference...")
            cross_ref_agent = self._create_cross_reference_agent(gemini_client, mcp_client)
            verification_response = await cross_ref_agent.arun(
                f"Verify these claims using authoritative web sources:\n\n{claims_text}\n\nYou MUST call search_engine for each claim, then scrape_as_markdown on authoritative sources. Start with the first claim now."
            )
            verification_text = verification_response.content
            print("FactCheckAgent: [Stage 3/4] Cross-Reference COMPLETE.")

            # Stage 4: Verdict Synthesis
            print("FactCheckAgent: [Stage 4/4] Starting Verdict Synthesis...")
            verdict_agent = self._create_verdict_agent(gemini_client)
            final_prompt = f"""
Original URL: {url}

Extracted Content:
{extracted_content}

Claims Identified:
{claims_text}

Verification Results:
{verification_text}

Synthesize a comprehensive fact-check report.
"""
            verdict_response = await verdict_agent.arun(final_prompt)
            final_report = verdict_response.content
            print("FactCheckAgent: [Stage 4/4] Verdict Synthesis COMPLETE.")

            # Parse verdict and confidence from report
            verdict_info = self._parse_verdict_from_report(final_report)
            print(f"FactCheckAgent: Pipeline finished with verdict: {verdict_info['verdict']}")

            return {
                'content': final_report,
                'verdict': verdict_info['verdict'],
                'confidence': verdict_info['confidence'],
                'claims': [],  # Claims are embedded in the report
                'sources': [],  # Sources are embedded in the report
                'metadata': {
                    'url': url,
                    'platform': self._detect_platform(url),
                    'stages_completed': 4
                }
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return {
                'content': f"## Error\n\nFailed to fact-check URL: {str(e)}\n\n```\n{error_details}\n```",
                'verdict': 'ERROR',
                'confidence': 0,
                'claims': [],
                'sources': [],
                'error': str(e)
            }

    async def _factcheck_text(
        self,
        text: str,
        gemini_client: GeminiClient,
        mcp_client: Optional[MCPClient]
    ) -> Dict[str, Any]:
        """Fact-check text content directly using 3-stage pipeline (skip content extraction)"""
        try:
            # Stage 2: Claim Identification
            claim_agent = self._create_claim_identifier(gemini_client)
            claim_response = await claim_agent.arun(
                f"Analyze the following text and identify all verifiable factual claims:\n\n{text}"
            )
            claims_text = claim_response.content

            # Stage 3: Cross-Reference
            if mcp_client:
                # Use MCP for web search if available
                cross_ref_agent = self._create_cross_reference_agent(gemini_client, mcp_client)
                verification_response = await cross_ref_agent.arun(
                    f"Verify these claims using authoritative web sources:\n\n{claims_text}\n\nYou MUST call search_engine for each claim, then scrape_as_markdown on authoritative sources. Start with the first claim now."
                )
                verification_text = verification_response.content
            else:
                # Without MCP, do basic analysis without web search
                verification_text = "⚠️ Web search unavailable. Verification based on known information only.\n\nNote: Full fact-checking requires web search integration (Bright Data MCP). Current analysis is limited to claims identification without external source verification."

            # Stage 4: Verdict Synthesis
            verdict_agent = self._create_verdict_agent(gemini_client)
            final_prompt = f"""
Original Text:
{text}

Claims Identified:
{claims_text}

Verification Results:
{verification_text}

Synthesize a comprehensive fact-check report.
"""
            verdict_response = await verdict_agent.arun(final_prompt)
            final_report = verdict_response.content

            # Parse verdict and confidence from report
            verdict_info = self._parse_verdict_from_report(final_report)

            return {
                'content': final_report,
                'verdict': verdict_info['verdict'],
                'confidence': verdict_info['confidence'],
                'claims': [],  # Claims are embedded in the report
                'sources': [],  # Sources are embedded in the report
                'metadata': {
                    'mode': 'text',
                    'stages_completed': 3,
                    'mcp_available': mcp_client is not None
                }
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return {
                'content': f"## Error\n\nFailed to fact-check text: {str(e)}\n\n```\n{error_details}\n```",
                'verdict': 'ERROR',
                'confidence': 0,
                'claims': [],
                'sources': [],
                'error': str(e)
            }

    # ===== Agent Factory Methods (FactFlux-style) =====

    def _create_content_extractor(
        self,
        gemini_client: GeminiClient,
        mcp_client: MCPClient
    ) -> Agent:
        """Create Content Extractor agent (Stage 1)"""
        return Agent(
            name="Content Extractor",
            role="Social media content extraction specialist that MUST use web scraping tools",
            gemini_client=gemini_client,
            mcp_client=mcp_client,
            instructions=[
                "You MUST use the available tools to extract data from social media posts",
                "DO NOT say you cannot extract data - you have the tools to do so",
                "",
                "REQUIRED WORKFLOW:",
                "1. For TikTok URLs: Call web_data_tiktok_posts tool with the URL",
                "2. For other platforms (Twitter, Instagram, Facebook): Call scrape_as_markdown tool with the URL",
                "3. If structured data extraction fails: Fall back to scrape_as_markdown",
                "",
                "Extract ALL available information:",
                "- Post text/caption",
                "- Media URLs (images, videos)",
                "- User information (username, profile)",
                "- Engagement metrics (likes, shares, comments)",
                "- Timestamps and dates",
                "",
                "Start by calling the appropriate tool now."
            ],
            add_datetime_to_instructions=True,
            markdown=True
        )

    def _create_claim_identifier(self, gemini_client: GeminiClient) -> Agent:
        """Create Claim Identifier agent (Stage 2)"""
        return Agent(
            name="Claim Identifier",
            role="Identify factual claims that can be verified",
            gemini_client=gemini_client,
            instructions=[
                "Parse extracted content to find specific, verifiable factual claims",
                "Ignore opinions, jokes, satire, and subjective statements",
                "Extract key facts: statistics, events, quotes, dates, locations",
                "Prioritize claims that are most important and checkable",
                "Format each claim clearly with context"
            ],
            add_datetime_to_instructions=True,
            markdown=True
        )

    def _create_cross_reference_agent(
        self,
        gemini_client: GeminiClient,
        mcp_client: MCPClient
    ) -> Agent:
        """Create Cross-Reference agent (Stage 3)"""
        return Agent(
            name="Cross-Reference Verifier",
            role="Fact verification specialist that MUST use web search to verify claims",
            gemini_client=gemini_client,
            mcp_client=mcp_client,
            instructions=[
                "You MUST use search tools to verify each claim against authoritative sources",
                "DO NOT say you cannot verify - you have the tools to do so",
                "",
                "REQUIRED WORKFLOW for each claim:",
                "1. Call search_engine with query about the claim",
                "2. Call scrape_as_markdown on relevant authoritative source URLs from results",
                "3. Document findings with source URLs and publication dates",
                "",
                "Target authoritative sources:",
                "- News sites (Reuters, AP, BBC, CNN, etc.)",
                "- Fact-checking sites (Snopes, FactCheck.org, PolitiFact)",
                "- Government sources (.gov sites)",
                "- Academic sources (universities, research papers)",
                "",
                "For each source, assess:",
                "- Credibility level (high/medium/low)",
                "- Publication date",
                "- Consensus with other sources",
                "- Any updates or corrections",
                "",
                "Start by calling search_engine for the first claim now."
            ],
            add_datetime_to_instructions=True,
            markdown=True
        )

    def _create_verdict_agent(self, gemini_client: GeminiClient) -> Agent:
        """Create Verdict Synthesizer agent (Stage 4)"""
        return Agent(
            name="Verdict Synthesizer",
            role="Analyze all evidence and deliver final fact-check verdict",
            gemini_client=gemini_client,
            instructions=[
                "Systematically review all extracted content, identified claims, and verification results",
                "Structure your response with these sections:",
                "## Post Summary - Describe what the post contained",
                "## Claims Identified - List each claim found",
                "## Verification Results - Detail findings for each claim with sources",
                "## Citations - Provide numbered list of all sources used",
                "## Context & Analysis - Explain why claims are true/false",
                "## Final Verdict - Clear verdict with confidence score (0-100%)",
                "Weigh source credibility, evidence quality, and consensus patterns",
                "Deliver clear verdict: TRUE/FALSE/MISLEADING/INSUFFICIENT_EVIDENCE",
                "Provide detailed reasoning chain and flag any uncertainties",
                "Consider social context and potential manipulation indicators",
                "Be conservative - if evidence is weak, say so clearly",
                "Include recommendations for readers on how to verify independently"
            ],
            add_datetime_to_instructions=True,
            markdown=True
        )

    def _parse_verdict_from_report(self, report: str) -> Dict[str, Any]:
        """Parse verdict and confidence from the final report"""
        import re

        # Try to extract verdict
        verdict_match = re.search(
            r'\*\*Verdict:\*\*\s*(TRUE|FALSE|MISLEADING|INSUFFICIENT_EVIDENCE|NEEDS_REVIEW)',
            report,
            re.IGNORECASE
        )
        verdict = verdict_match.group(1).upper() if verdict_match else 'UNKNOWN'

        # Try to extract confidence score
        confidence_match = re.search(
            r'\*\*Confidence:\*\*\s*(\d+)%',
            report
        )
        confidence = int(confidence_match.group(1)) if confidence_match else 50

        return {
            'verdict': verdict,
            'confidence': confidence
        }

    def _detect_platform(self, url: str) -> str:
        """Detect social media platform from URL"""
        url_lower = url.lower()
        if 'tiktok.com' in url_lower:
            return 'TikTok'
        elif 'instagram.com' in url_lower:
            return 'Instagram'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'Twitter/X'
        elif 'facebook.com' in url_lower:
            return 'Facebook'
        elif 'youtube.com' in url_lower:
            return 'YouTube'
        elif 'linkedin.com' in url_lower:
            return 'LinkedIn'
        else:
            return 'Unknown'
