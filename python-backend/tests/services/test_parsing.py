"""Tests for ContentParser service."""

from unittest.mock import patch

import pytest
from src.db.models import ParsedContent
from src.exceptions import ContentParsingError
from src.services.parsing import ContentParser


class TestContentParser:
    """Coverage for HTML/text parsing and parser dispatch."""

    def test_parse_html_extracts_title_and_text(self) -> None:
        """HTML parsing should extract readable text and title."""
        parser = ContentParser()
        html = """
        <html>
          <head><title>Readable Title</title></head>
          <body>
            <main>
              <article>
                <h1>Readable Title</h1>
                <p>First paragraph of article text.</p>
                <p>Second paragraph of article text.</p>
              </article>
            </main>
          </body>
        </html>
        """

        result = parser.parse_html(html)

        assert result.title == "Readable Title"
        assert "First paragraph of article text." in result.text
        assert "Second paragraph of article text." in result.text
        assert result.word_count > 0

    def test_parse_text_passthrough_strips_whitespace(self) -> None:
        """Plain text parser should strip boundary whitespace only."""
        parser = ContentParser()

        result = parser.parse_text("  Line one\nLine two  ")

        assert result.title is None
        assert result.text == "Line one\nLine two"
        assert result.word_count == 4

    @pytest.mark.parametrize("raw_html", ["", "   \n\t  "])
    def test_parse_html_handles_empty_input(self, raw_html: str) -> None:
        """Empty/whitespace HTML input should produce empty parsed content."""
        parser = ContentParser()

        result = parser.parse_html(raw_html)

        assert result.text == ""
        assert result.title is None
        assert result.word_count == 0

    def test_parse_html_tolerates_malformed_html(self) -> None:
        """Malformed HTML should still return best-effort parsed content."""
        parser = ContentParser()
        malformed_html = "<html><head><title>Broken<title></head><body><p>Text<p>"

        result = parser.parse_html(malformed_html)

        assert "Text" in result.text
        assert result.word_count >= 1

    def test_parse_dispatches_by_content_type(self) -> None:
        """parse() should route webpage to HTML parser and others to text parser."""
        parser = ContentParser()
        html_result = ParsedContent(text="html", title="t", word_count=1)
        text_result = ParsedContent(text="text", title=None, word_count=1)

        with (
            patch.object(parser, "parse_html", return_value=html_result) as parse_html,
            patch.object(parser, "parse_text", return_value=text_result) as parse_text,
        ):
            assert parser.parse("<p>x</p>", "webpage") == html_result
            assert parser.parse("hello", "note") == text_result
            assert parser.parse("hello", "file") == text_result

            parse_html.assert_called_once_with("<p>x</p>")
            assert parse_text.call_count == 2

    def test_parse_html_wraps_unrecoverable_parser_failures(self) -> None:
        """Unrecoverable parser exceptions should be wrapped in ContentParsingError."""
        parser = ContentParser()

        with (
            patch("src.services.parsing.Document", side_effect=RuntimeError("boom")),
            pytest.raises(ContentParsingError) as exc_info,
        ):
            parser.parse_html("<html><body>content</body></html>")

        assert "Failed to parse HTML" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, RuntimeError)
