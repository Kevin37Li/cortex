# Task: Implement Content Parsing Service

## Summary

Create a content parsing service that converts raw captured content (HTML web pages, plain text, Markdown) into clean plain text suitable for chunking and embedding. HTML parsing uses a Readability-style algorithm to extract the main article content, stripping navigation, ads, and boilerplate.

## Acceptance Criteria

- [ ] `services/parsing.py` created with `ContentParser` class
- [ ] `parse_html(raw_html: str) -> ParsedContent` — Extracts article text from HTML using readability algorithm
- [ ] `parse_text(raw_text: str) -> ParsedContent` — Passes through plain text/Markdown with minimal processing
- [ ] `parse(content: str, content_type: str) -> ParsedContent` — Dispatcher that routes to correct parser based on content_type
- [ ] `ParsedContent` Pydantic model in `db/models.py` with fields: `text`, `title`, `word_count`, `language`
- [ ] HTML parser strips scripts, styles, nav elements, and extracts main content
- [ ] HTML parser preserves paragraph structure (newlines between paragraphs)
- [ ] Handles malformed HTML gracefully (returns best-effort extraction for recoverable issues)
- [ ] Raises `ContentParsingError` (from `exceptions.py`) for unrecoverable parsing failures
- [ ] Empty or whitespace-only content returns `ParsedContent` with empty text (caller decides how to handle)
- [ ] `ContentParser` exported from `services/__init__.py`

> **Note:** Tests are defined in Task 11 (Processing Backend Tests).

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
- **Encoding:** Input is expected to be valid UTF-8 strings; encoding handling is the responsibility of the content capture layer
- **Language field:** Returns `None` for MVP — language detection is a future enhancement
- **Error handling:** Use existing `ContentParsingError` from `exceptions.py` for unrecoverable failures

## ParsedContent Model

```python
# Add to db/models.py (follows established pattern for Pydantic models)
class ParsedContent(BaseModel):
    """Result of parsing raw content."""
    text: str  # Clean extracted text
    title: str | None = None  # Extracted title (HTML) or None
    word_count: int
    language: str | None = None  # Always None for MVP; reserved for future language detection
```

## Implementation Pattern

```python
# services/parsing.py
import logging
from readability import Document
from bs4 import BeautifulSoup

from src.db.models import ParsedContent
from src.exceptions import ContentParsingError

logger = logging.getLogger(__name__)

class ContentParser:
    def parse(self, content: str, content_type: str) -> ParsedContent:
        if content_type == "webpage":
            return self.parse_html(content)
        return self.parse_text(content)

    def parse_html(self, raw_html: str) -> ParsedContent:
        try:
            doc = Document(raw_html)
            summary_html = doc.summary()
            title = doc.title()
        except Exception as e:
            logger.exception("Unrecoverable HTML parsing failure")
            raise ContentParsingError(message=f"Failed to parse HTML: {e}")

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
- `python-backend/src/db/models.py` — Add `ParsedContent` model
- `python-backend/src/services/__init__.py` — Export `ContentParser`

## Verification

```bash
cd python-backend
uv sync  # Install new dependencies
uv run python -c "
from src.services import ContentParser
parser = ContentParser()

# Test HTML parsing
result = parser.parse('<html><body><article><h1>Test</h1><p>Hello world</p></article></body></html>', 'webpage')
print(f'HTML: title={result.title}, words={result.word_count}, text={result.text[:50]}')

# Test plain text
result = parser.parse('Hello world, this is a note.', 'note')
print(f'Text: words={result.word_count}, text={result.text[:50]}')

# Test empty content
result = parser.parse('', 'note')
print(f'Empty: words={result.word_count}, text_empty={result.text == \"\"}')
"
```

---

## Implementation Details

_Tracked: 2026-01-31_

### Files Changed

| File                                      | Change   | Description                                                          |
| ----------------------------------------- | -------- | -------------------------------------------------------------------- |
| `python-backend/src/services/parsing.py`  | Created  | ContentParser class with parse(), parse_html(), parse_text() methods |
| `python-backend/src/db/models.py`         | Modified | Added ParsedContent Pydantic model                                   |
| `python-backend/src/services/__init__.py` | Modified | Export ContentParser class                                           |
| `python-backend/pyproject.toml`           | Modified | Added readability-lxml, beautifulsoup4, lxml dependencies            |
| `python-backend/uv.lock`                  | Modified | Updated lockfile with new dependencies                               |

### Dependencies Added

- `readability-lxml>=0.8.1` - Mozilla Readability algorithm for HTML article extraction
- `beautifulsoup4>=4.12.0` - HTML to text conversion with paragraph preservation
- `lxml>=5.0.0` - Fast XML/HTML parser backend for BeautifulSoup

### Acceptance Criteria Status

- [x] `services/parsing.py` created with `ContentParser` class - `python-backend/src/services/parsing.py:14`
- [x] `parse_html(raw_html: str) -> ParsedContent` — `parsing.py:35-71`
- [x] `parse_text(raw_text: str) -> ParsedContent` — `parsing.py:73-87`
- [x] `parse(content: str, content_type: str) -> ParsedContent` — `parsing.py:21-33`
- [x] `ParsedContent` Pydantic model in `db/models.py` — `models.py:10-19`
- [x] HTML parser strips scripts, styles, nav elements via readability algorithm
- [x] HTML parser preserves paragraph structure with `separator="\n\n"`
- [x] Handles malformed HTML gracefully (readability is fault-tolerant)
- [x] Raises `ContentParsingError` for unrecoverable failures — `parsing.py:64-65`
- [x] Empty/whitespace content returns ParsedContent with empty text — `parsing.py:47-53`, `parsing.py:82`
- [x] `ContentParser` exported from `services/__init__.py`

---

## Learning Report

_Generated: 2026-01-31_

### Summary

Implemented the ContentParser service for Task 3, which converts raw captured content (HTML, plain text, Markdown) into clean plain text for downstream chunking and embedding. The implementation follows the task specification closely, using `readability-lxml` for HTML article extraction and `beautifulsoup4` for HTML-to-text conversion.

- **Files changed:** 5 (1 created, 4 modified)
- **Lines of code:** ~88 lines in parsing.py
- **Methods implemented:** 3 (parse, parse_html, parse_text)

### Patterns & Decisions

1. **Pure Function Service Pattern**: The ContentParser has no dependencies on database or AI services, making it easy to test and use as a standalone component in the LangGraph workflow.

2. **Dispatcher Pattern**: The `parse()` method routes to the appropriate parser based on `content_type`, with `parse_text()` as the default fallback for non-HTML content types ('note', 'file').

3. **Error Handling Strategy**:
   - Empty/whitespace content returns a valid `ParsedContent` with empty text (letting callers decide handling)
   - Only truly unrecoverable errors raise `ContentParsingError`
   - Uses exception chaining (`from e`) for proper error traceability

4. **Model Location**: `ParsedContent` placed in `db/models.py` following existing Pydantic model patterns, even though it's not a database entity.

### Challenges & Solutions

1. **Empty Title Handling**: The readability library returns `[no-title]` for pages without titles. Solution: Check if title is truthy and convert to `None` if empty or placeholder-like.

2. **Word Count for Empty Text**: Calling `split()` on empty string returns `['']` with length 1. Solution: Added explicit check `if text else 0` to return 0 for empty content.

3. **Null Safety**: Input content could be `None` (not just empty string). Solution: Added defensive checks like `raw_html.strip() if raw_html else ""` to handle both cases.

### Lessons Learned

1. **What worked well:**
   - The task spec was comprehensive with a complete implementation pattern, making development straightforward
   - The readability-lxml library handles malformed HTML gracefully out of the box
   - Verification script in the task spec enabled quick validation

2. **What could be improved:**
   - The `[no-title]` placeholder from readability is a quirk worth documenting for future developers
   - Consider adding type hints for improved IDE support (already present)

3. **Future considerations:**
   - Language detection (marked as MVP=None) would be useful for multilingual content
   - May want to preserve some Markdown structure rather than stripping all formatting for 'file' type

### Documentation Impact

1. **Existing docs to review:**
   - `docs/developer/python-backend/architecture.md` - May need to add ContentParser to service layer documentation
   - `docs/developer/architecture/error-handling.md` - Verify ContentParsingError usage is consistent

2. **New patterns documented:**
   - Pure function service pattern (no DB/AI dependencies)
   - Dispatcher pattern for content type routing

3. **Documentation that was helpful:**
   - Task spec's implementation pattern section provided clear guidance
   - The verification script was valuable for quick validation
