# Task: Implement Content Parsing Service

## Summary

Create a content parsing service that converts raw captured content (HTML web pages, plain text, Markdown) into clean plain text suitable for chunking and embedding. HTML parsing uses a Readability-style algorithm to extract the main article content, stripping navigation, ads, and boilerplate.

## Acceptance Criteria

- [ ] `services/parsing.py` created with `ContentParser` class
- [ ] `parse_html(raw_html: str, source_url: str | None) -> ParsedContent` — Extracts article text from HTML using readability algorithm
- [ ] `parse_text(raw_text: str) -> ParsedContent` — Passes through plain text/Markdown with minimal processing
- [ ] `parse(content: str, content_type: str) -> ParsedContent` — Dispatcher that routes to correct parser based on content_type
- [ ] `ParsedContent` Pydantic model with fields: `text` (cleaned content), `title` (extracted or original), `word_count`, `language` (optional)
- [ ] HTML parser strips scripts, styles, nav elements, and extracts main content
- [ ] HTML parser preserves paragraph structure (newlines between paragraphs)
- [ ] Handles malformed HTML gracefully (returns best-effort extraction, doesn't raise)
- [ ] Empty or whitespace-only content returns `ParsedContent` with empty text (caller decides how to handle)

## Dependencies

- Phase 1 complete: Python backend project structure exists
- No dependency on other Phase 2 tasks

## Technical Notes

- Use `readability-lxml` (Python port of Mozilla's Readability) for HTML article extraction
- Use `beautifulsoup4` with `lxml` parser for HTML cleanup after Readability
- Add dependencies to `pyproject.toml`: `readability-lxml`, `beautifulsoup4`, `lxml`
- Content types from schema: `'webpage'` (HTML), `'note'` (plain text), `'file'` (Markdown/text)
- The parser is a pure function service — no database access, no AI calls
- This is the "Parse" node in the LangGraph processing workflow

## ParsedContent Model

```python
# Add to services/parsing.py or db/models.py
class ParsedContent(BaseModel):
    """Result of parsing raw content."""
    text: str  # Clean extracted text
    title: str | None = None  # Extracted title (HTML) or None
    word_count: int
    language: str | None = None  # Detected language (optional, future use)
```

## Implementation Pattern

```python
# services/parsing.py
from readability import Document
from bs4 import BeautifulSoup

class ContentParser:
    def parse(self, content: str, content_type: str) -> ParsedContent:
        if content_type == "webpage":
            return self.parse_html(content)
        return self.parse_text(content)

    def parse_html(self, raw_html: str, source_url: str | None = None) -> ParsedContent:
        doc = Document(raw_html)
        summary_html = doc.summary()
        title = doc.title()

        # Clean HTML to plain text
        soup = BeautifulSoup(summary_html, "lxml")
        text = soup.get_text(separator="\n\n", strip=True)

        return ParsedContent(
            text=text,
            title=title,
            word_count=len(text.split()),
        )

    def parse_text(self, raw_text: str) -> ParsedContent:
        text = raw_text.strip()
        return ParsedContent(
            text=text,
            title=None,
            word_count=len(text.split()),
        )
```

## Files to Create/Modify

**Create:**

- `python-backend/src/services/parsing.py` — Content parsing service

**Modify:**

- `python-backend/pyproject.toml` — Add `readability-lxml`, `beautifulsoup4`, `lxml`

## Verification

```bash
cd python-backend
uv sync  # Install new dependencies
uv run python -c "
from src.services.parsing import ContentParser
parser = ContentParser()

# Test HTML parsing
result = parser.parse('<html><body><article><h1>Test</h1><p>Hello world</p></article></body></html>', 'webpage')
print(f'HTML: title={result.title}, words={result.word_count}, text={result.text[:50]}')

# Test plain text
result = parser.parse('Hello world, this is a note.', 'note')
print(f'Text: words={result.word_count}, text={result.text[:50]}')
"
```
