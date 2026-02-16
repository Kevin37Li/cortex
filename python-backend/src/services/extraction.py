"""Metadata extraction service using LLM chat to extract structured metadata."""

import json
import logging
import re

from src.db.models import ExtractedMetadata
from src.exceptions import AIProviderError, MetadataExtractionError
from src.providers import AIProvider

logger = logging.getLogger(__name__)

# Maximum characters to send to the LLM (~3000 tokens at 4 chars/token)
MAX_EXTRACTION_CHARS = 12000

EXTRACTION_SYSTEM_PROMPT = """You are a knowledge extraction assistant. Given a piece of content, extract:
1. A concise summary (2-3 sentences)
2. Key concepts/topics (3-7 items)
3. Named entities: people, organizations, places (if any)

Respond ONLY with valid JSON in this exact format:
{
    "summary": "...",
    "concepts": ["concept1", "concept2", ...],
    "entities": ["entity1", "entity2", ...]
}"""

EXTRACTION_USER_PROMPT = """Extract metadata from the following content:
{title_section}
Content:
{text}"""

EXTRACTION_JSON_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "concepts": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "entities": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "concepts", "entities"],
}


class MetadataExtractor:
    """Extracts structured metadata from content using LLM chat.

    This is the "Extract" node in the LangGraph processing workflow.
    Uses AIProvider.chat() to extract summary, concepts, and entities.
    """

    def __init__(self, provider: AIProvider) -> None:
        """Initialize the extractor with an AI provider.

        Args:
            provider: AI provider implementing the chat interface.
        """
        self._provider = provider

    async def extract(self, text: str, title: str | None = None) -> ExtractedMetadata:
        """Extract metadata from text using LLM.

        Args:
            text: The content text to extract metadata from.
            title: Optional title to provide context for extraction.

        Returns:
            ExtractedMetadata with summary, concepts, and entities.

        Raises:
            MetadataExtractionError: If the AI provider fails.
        """
        logger.debug("Starting metadata extraction (text length: %d)", len(text))

        # Handle empty content
        if not text or not text.strip():
            logger.debug("Empty text provided, returning empty metadata")
            return ExtractedMetadata()

        # Truncate long text to fit context window
        truncated_text = self._truncate_text(text)

        # Build the user prompt
        user_prompt = self._build_user_prompt(truncated_text, title)

        try:
            response = await self._provider.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system=EXTRACTION_SYSTEM_PROMPT,
                json_schema=EXTRACTION_JSON_SCHEMA,
            )
        except AIProviderError as e:
            raise MetadataExtractionError(
                f"AI provider failed during metadata extraction: {e}",
                step="metadata_extraction",
            ) from e

        # Parse the response
        return self._parse_response(response)

    def _truncate_text(self, text: str) -> str:
        """Truncate text to fit model context window.

        Args:
            text: The text to potentially truncate.

        Returns:
            Truncated text with ellipsis if needed.
        """
        if len(text) <= MAX_EXTRACTION_CHARS:
            return text
        logger.debug(
            "Truncating text from %d to %d characters", len(text), MAX_EXTRACTION_CHARS
        )
        return text[:MAX_EXTRACTION_CHARS] + "..."

    def _build_user_prompt(self, text: str, title: str | None) -> str:
        """Build the user prompt with optional title.

        Args:
            text: The content text.
            title: Optional title.

        Returns:
            Formatted user prompt string.
        """
        title_section = f"\nTitle: {title}\n" if title else ""
        return EXTRACTION_USER_PROMPT.format(title_section=title_section, text=text)

    def _parse_response(self, response: str) -> ExtractedMetadata:
        """Parse LLM response into ExtractedMetadata.

        Attempts to parse JSON from the response. If parsing fails,
        returns empty metadata with a warning logged.

        Args:
            response: Raw LLM response string.

        Returns:
            ExtractedMetadata parsed from response or empty defaults.
        """
        # Try to extract JSON from the response
        json_str = self._extract_json(response)

        if json_str is None:
            logger.warning(
                "Failed to find JSON in LLM response, returning empty metadata"
            )
            return ExtractedMetadata()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON from LLM response: %s", e)
            return ExtractedMetadata()

        # Guard against non-object JSON responses (e.g., arrays, strings)
        if not isinstance(data, dict):
            logger.warning(
                "LLM returned valid JSON but not an object, returning empty metadata"
            )
            return ExtractedMetadata()

        # Validate and extract fields with defaults
        return ExtractedMetadata(
            summary=data.get("summary", "")
            if isinstance(data.get("summary"), str)
            else "",
            concepts=self._extract_string_list(data.get("concepts")),
            entities=self._extract_string_list(data.get("entities")),
        )

    def _extract_json(self, response: str) -> str | None:
        """Extract JSON object from response string.

        Handles responses where JSON may be wrapped in markdown code blocks
        or have extra text around it.

        Args:
            response: Raw response string.

        Returns:
            JSON string if found, None otherwise.
        """
        # First try: use JSONDecoder.raw_decode for robust JSON extraction
        # This properly handles braces inside string literals
        response = response.strip()
        if response.startswith("{"):
            try:
                decoder = json.JSONDecoder()
                _, end_index = decoder.raw_decode(response)
                return response[:end_index]
            except json.JSONDecodeError:
                pass  # Fall through to other extraction methods

        # Second try: look for JSON in markdown code blocks
        code_block_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL
        )
        if code_block_match:
            return code_block_match.group(1)

        # Third try: find any JSON object in the response
        json_match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
        if json_match:
            return json_match.group(0)

        return None

    def _extract_string_list(self, value: object) -> list[str]:
        """Extract a list of strings from a value.

        Args:
            value: Value that should be a list of strings.

        Returns:
            List of strings, filtering out non-string items.
        """
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]
