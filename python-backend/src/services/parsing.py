"""Content parsing service for converting raw content to clean text."""

import logging

from bs4 import BeautifulSoup
from readability import Document

from src.db.models import ParsedContent
from src.exceptions import ContentParsingError

logger = logging.getLogger(__name__)


class ContentParser:
    """Parses raw content (HTML, text, Markdown) into clean plain text.

    This is the "Parse" node in the LangGraph processing workflow.
    Pure function service — no database access, no AI calls.
    """

    def parse(self, content: str, content_type: str) -> ParsedContent:
        """Route content to appropriate parser based on content_type.

        Args:
            content: Raw content string (HTML, plain text, or Markdown)
            content_type: Type of content: 'webpage', 'note', 'file'

        Returns:
            ParsedContent with extracted text and metadata
        """
        if content_type == "webpage":
            return self.parse_html(content)
        return self.parse_text(content)

    def parse_html(self, raw_html: str) -> ParsedContent:
        """Extract article content from HTML using readability algorithm.

        Args:
            raw_html: Raw HTML string

        Returns:
            ParsedContent with extracted article text and title

        Raises:
            ContentParsingError: For unrecoverable parsing failures
        """
        # Handle empty/whitespace-only content
        if not raw_html or not raw_html.strip():
            return ParsedContent(
                text="",
                title=None,
                word_count=0,
            )

        try:
            doc = Document(raw_html)
            summary_html = doc.summary()
            title = doc.title()

            # Clean HTML to plain text, preserving paragraph structure
            soup = BeautifulSoup(summary_html, "lxml")
            text = soup.get_text(separator="\n\n", strip=True)
        except Exception as e:
            logger.exception("Unrecoverable HTML parsing failure")
            raise ContentParsingError(message=f"Failed to parse HTML: {e}") from e

        return ParsedContent(
            text=text,
            title=title if title else None,
            word_count=len(text.split()) if text else 0,
        )

    def parse_text(self, raw_text: str) -> ParsedContent:
        """Pass through plain text/Markdown with minimal processing.

        Args:
            raw_text: Raw text or Markdown string

        Returns:
            ParsedContent with the text stripped of leading/trailing whitespace
        """
        text = raw_text.strip() if raw_text else ""
        return ParsedContent(
            text=text,
            title=None,
            word_count=len(text.split()) if text else 0,
        )
