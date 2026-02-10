# Task: Close Backend Processing Test Gaps

## Summary

Most Phase 2 backend tests are already implemented. This task should now focus on **real gaps**: add missing `ContentParser` tests, add workflow orchestration tests for `src/workflows/processing.py`, and extend processing API retry edge-case coverage.

Also include **test-suite hygiene refactor**:

- Centralize pytest fixtures in `python-backend/tests/conftest.py`
- Reorganize test files into domain folders (API/DB/providers/services/workflows/core)

Current baseline (from `bun run python:test -- --cov=src --cov-report=term-missing`):

- `src/services/parsing.py`: 37%
- `src/workflows/processing.py`: 31%
- `src/services/chunking.py`, `src/services/embeddings.py`, `src/services/extraction.py`, and `src/services/processing.py`: already covered
- Total backend coverage: 80%

## Acceptance Criteria

- [x] Add `python-backend/tests/services/test_parsing.py` for `ContentParser`:
  - [x] HTML parsing success (title/text extracted)
  - [x] Plain text passthrough
  - [x] Empty/whitespace input handling
  - [x] Malformed HTML behavior
  - [x] Parser dispatch by `content_type`
  - [x] `ContentParsingError` wrapping on unrecoverable parser failure
- [x] Add `python-backend/tests/workflows/test_processing.py` for `src/workflows/processing.py`:
  - [x] Happy-path `process_item()` updates item status to `completed` and persists metadata/chunks
  - [x] Validation retry path (initial validation failure then success)
  - [x] Max retries exceeded path routes to `handle_error` and marks item `failed`
  - [x] Missing item path from `classify` routes to error handling
  - [x] `emit_processing_update()` contract tests (step/status/progress/message)
  - [x] Routing helpers (`route_or_error`, `route_after_validation`) branch tests
- [x] Extend `python-backend/tests/api/test_processing.py`:
  - [x] Retry-specific returns `already_queued` outcome when queue reports it
  - [x] Retry-specific returns `retried` outcome/count when queue enqueues item
  - [x] Retry-all works for omitted body and `null` body payloads
- [x] No test performs real Ollama/OpenAI calls (all provider calls mocked)
- [x] Existing Python tests continue to pass
- [x] Coverage improves meaningfully for workflow/parsing modules; target:
  - [x] `src/services/parsing.py` >= 80%
  - [x] `src/workflows/processing.py` >= 70%
  - [x] Total backend coverage remains >= 80%
- [x] Centralize fixtures in `python-backend/tests/conftest.py`:
  - [x] Move shared fixtures currently defined in test modules into `conftest.py`
  - [x] Remove duplicate fixture definitions (e.g., duplicate `temp_db_path`)
  - [x] Keep fixture names stable where possible to minimize test churn
  - [x] Ensure fixture scope is explicit (`function` by default unless broader scope is needed)
- [x] Reorganize tests into folders by domain (similar to existing `services/` organization):
  - [x] `python-backend/tests/api/` for API route tests
  - [x] `python-backend/tests/db/` for DB/repository tests
  - [x] `python-backend/tests/providers/` for provider tests
  - [x] `python-backend/tests/services/` for service tests (existing)
  - [x] `python-backend/tests/workflows/` for workflow tests
  - [x] `python-backend/tests/core/` for cross-cutting tests (e.g., exceptions)
  - [x] Add `__init__.py` files only where needed for package-relative imports

## Dependencies

- Tasks 1-10 complete (processing pipeline code exists)
- Existing pytest infrastructure in `python-backend/tests/conftest.py`
- Existing service/API test suites in `python-backend/tests/services/` and `python-backend/tests/`

## Technical Notes

- Use the current test layout:
  - Service tests in `python-backend/tests/services/`
  - Workflow tests in `python-backend/tests/workflows/` (create folder if needed)
  - API route tests should be moved from `python-backend/tests/` to `python-backend/tests/api/`
- Reuse patterns from:
  - `python-backend/tests/services/test_embeddings.py`
  - `python-backend/tests/services/test_processing.py`
  - `python-backend/tests/api/test_items.py`
- For workflow tests, patch provider creation at `src.workflows.processing.OllamaProvider` to return a deterministic mock provider.
- Keep tests deterministic:
  - No network access
  - Small inline content fixtures
  - Explicit assertions on `processing_status`, metadata fields, and retry outcomes
- Prefer focused unit tests for node/routing logic plus a small number of orchestration-level tests for `process_item()`.
- Fixture consolidation plan:
  - Move module fixtures from:
    - `python-backend/tests/services/test_embeddings.py`
    - `python-backend/tests/test_api_health_ollama.py`
    - `python-backend/tests/test_database.py`
    - `python-backend/tests/test_providers_ollama.py`
  - Into `python-backend/tests/conftest.py` with grouped sections:
    - Database fixtures (`temp_db_path`, `db_connection`, `db_with_vec`)
    - HTTP/client fixtures (`client`)
    - Provider mocks (`mock_ollama_provider`, mock AI providers)
    - Test data fixtures (`sample_chunks`)
- File organization migration map:
  - `python-backend/tests/test_api_health.py` -> `python-backend/tests/api/test_health.py`
  - `python-backend/tests/test_api_health_ollama.py` -> `python-backend/tests/api/test_health_ollama.py`
  - `python-backend/tests/test_api_items.py` -> `python-backend/tests/api/test_items.py`
  - `python-backend/tests/test_api_processing.py` -> `python-backend/tests/api/test_processing.py`
  - `python-backend/tests/test_api_ws_processing.py` -> `python-backend/tests/api/test_ws_processing.py`
  - `python-backend/tests/test_database.py` -> `python-backend/tests/db/test_database.py`
  - `python-backend/tests/test_repositories.py` -> `python-backend/tests/db/test_repositories.py`
  - `python-backend/tests/test_providers_ollama.py` -> `python-backend/tests/providers/test_ollama.py`
  - `python-backend/tests/test_exceptions.py` -> `python-backend/tests/core/test_exceptions.py`
- Migration safety steps:
  - Move files first, then run `bun run python:test` to catch import/fixture issues
  - After fixture centralization, run full coverage command and verify no regressions

## Files to Create/Modify

- `python-backend/tests/services/test_parsing.py` (create)
- `python-backend/tests/workflows/test_processing.py` (create)
- `python-backend/tests/api/test_processing.py` (modify after move)
- `python-backend/tests/conftest.py` (required: centralized shared fixtures)
- `python-backend/tests/api/` (create and move existing API tests)
- `python-backend/tests/db/` (create and move DB/repository tests)
- `python-backend/tests/providers/` (create and move provider tests)
- `python-backend/tests/core/` (create and move exception tests)

## Verification

```bash
bun run python:test
bun run python:test -- --cov=src.services.parsing --cov=src.workflows.processing --cov-report=term-missing
bun run python:test -- --cov=src --cov-fail-under=80
```

---

## Implementation Details

_Tracked: 2026-02-10_

### Files Changed

| File                                                | Change          | Description                                                                                                                                             |
| --------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python-backend/tests/services/test_parsing.py`     | Created         | Added complete `ContentParser` coverage for HTML/text parsing, dispatch, malformed input, and unrecoverable parser error wrapping.                      |
| `python-backend/tests/workflows/test_processing.py` | Created         | Added workflow orchestration tests for `process_item()`, validation retries, error routing, emit contract, and routing helper functions.                |
| `python-backend/tests/api/test_processing.py`       | Created         | Moved processing API tests into `tests/api/` and extended retry endpoint coverage for `already_queued`, `retried`, and omitted/null request body cases. |
| `python-backend/tests/conftest.py`                  | Modified        | Centralized shared fixtures (database, client, provider, service, and test data fixtures) with explicit `function` scope.                               |
| `python-backend/tests/fakes/providers.py`           | Created         | Added reusable `MockAIProvider` test double shared by service/workflow tests.                                                                           |
| `python-backend/tests/services/test_embeddings.py`  | Modified        | Removed duplicate module fixtures and switched to shared fixtures/fakes from `conftest.py` and `tests/fakes/providers.py`.                              |
| `python-backend/tests/test_api_health.py`           | Deleted (moved) | Moved to `python-backend/tests/api/test_health.py` as part of domain-based test organization.                                                           |
| `python-backend/tests/test_api_health_ollama.py`    | Deleted (moved) | Moved to `python-backend/tests/api/test_health_ollama.py`.                                                                                              |
| `python-backend/tests/test_api_items.py`            | Deleted (moved) | Moved to `python-backend/tests/api/test_items.py`.                                                                                                      |
| `python-backend/tests/test_api_ws_processing.py`    | Deleted (moved) | Moved to `python-backend/tests/api/test_ws_processing.py`.                                                                                              |
| `python-backend/tests/test_database.py`             | Deleted (moved) | Moved to `python-backend/tests/db/test_database.py`.                                                                                                    |
| `python-backend/tests/test_repositories.py`         | Deleted (moved) | Moved to `python-backend/tests/db/test_repositories.py`.                                                                                                |
| `python-backend/tests/test_providers_ollama.py`     | Deleted (moved) | Moved to `python-backend/tests/providers/test_ollama.py`.                                                                                               |
| `python-backend/tests/test_exceptions.py`           | Deleted (moved) | Moved to `python-backend/tests/core/test_exceptions.py`.                                                                                                |
| `python-backend/pyproject.toml`                     | Modified        | Added `integration` pytest marker for workflow integration tests.                                                                                       |
| `docs/developer/python-backend/architecture.md`     | Modified        | Updated test tree documentation to show domain-organized backend tests.                                                                                 |
| `docs/developer/quality-tooling/testing.md`         | Modified        | Updated Python testing docs for domain-based test layout and centralized fixture strategy.                                                              |

### Dependencies Added

- None.

### Acceptance Criteria Status

- [x] Add `python-backend/tests/services/test_parsing.py` for `ContentParser`:
  - [x] HTML parsing success (title/text extracted) - `python-backend/tests/services/test_parsing.py:14`
  - [x] Plain text passthrough - `python-backend/tests/services/test_parsing.py:39`
  - [x] Empty/whitespace input handling - `python-backend/tests/services/test_parsing.py:50`
  - [x] Malformed HTML behavior - `python-backend/tests/services/test_parsing.py:60`
  - [x] Parser dispatch by `content_type` - `python-backend/tests/services/test_parsing.py:70`
  - [x] `ContentParsingError` wrapping on unrecoverable parser failure - `python-backend/tests/services/test_parsing.py:87`
- [x] Add `python-backend/tests/workflows/test_processing.py` for `src/workflows/processing.py`:
  - [x] Happy-path `process_item()` updates item status to `completed` and persists metadata/chunks - `python-backend/tests/workflows/test_processing.py:53`
  - [x] Validation retry path (initial validation failure then success) - `python-backend/tests/workflows/test_processing.py:84`
  - [x] Max retries exceeded path routes to `handle_error` and marks item `failed` - `python-backend/tests/workflows/test_processing.py:127`
  - [x] Missing item path from `classify` routes to error handling - `python-backend/tests/workflows/test_processing.py:164`
  - [x] `emit_processing_update()` contract tests (step/status/progress/message) - `python-backend/tests/workflows/test_processing.py:181`, `python-backend/tests/workflows/test_processing.py:202`, `python-backend/tests/workflows/test_processing.py:227`
  - [x] Routing helpers (`route_or_error`, `route_after_validation`) branch tests - `python-backend/tests/workflows/test_processing.py:243`, `python-backend/tests/workflows/test_processing.py:249`, `python-backend/tests/workflows/test_processing.py:255`, `python-backend/tests/workflows/test_processing.py:259`, `python-backend/tests/workflows/test_processing.py:263`, `python-backend/tests/workflows/test_processing.py:267`
- [x] Extend `python-backend/tests/api/test_processing.py`:
  - [x] Retry-specific returns `already_queued` outcome when queue reports it - `python-backend/tests/api/test_processing.py:98`
  - [x] Retry-specific returns `retried` outcome/count when queue enqueues item - `python-backend/tests/api/test_processing.py:127`
  - [x] Retry-all works for omitted body and `null` body payloads - `python-backend/tests/api/test_processing.py:68`, `python-backend/tests/api/test_processing.py:83`
- [x] No test performs real Ollama/OpenAI calls (all provider calls mocked) - `python-backend/tests/workflows/test_processing.py:66`, `python-backend/tests/workflows/test_processing.py:98`, `python-backend/tests/providers/test_ollama.py:64`
- [x] Existing Python tests continue to pass - `bun run python:test` (result: `232 passed`, executed 2026-02-10)
- [x] Coverage improves meaningfully for workflow/parsing modules; target:
  - [x] `src/services/parsing.py` >= 80% - `100%` from `bun run python:test -- --cov=src.services.parsing --cov=src.workflows.processing --cov-report=term-missing` (2026-02-10)
  - [x] `src/workflows/processing.py` >= 70% - `86%` from the same coverage run (2026-02-10)
  - [x] Total backend coverage remains >= 80% - `91%` from `bun run python:test -- --cov=src --cov-fail-under=80` (2026-02-10)
- [x] Centralize fixtures in `python-backend/tests/conftest.py`:
  - [x] Move shared fixtures currently defined in test modules into `conftest.py` - `python-backend/tests/conftest.py:24`, `python-backend/tests/conftest.py:30`, `python-backend/tests/conftest.py:41`, `python-backend/tests/conftest.py:75`, `python-backend/tests/conftest.py:124`
  - [x] Remove duplicate fixture definitions (e.g., duplicate `temp_db_path`) - `python-backend/tests/services/test_embeddings.py:21` (now imports shared fake/fixtures only)
  - [x] Keep fixture names stable where possible to minimize test churn - `python-backend/tests/conftest.py:24`, `python-backend/tests/conftest.py:30`, `python-backend/tests/conftest.py:75`
  - [x] Ensure fixture scope is explicit (`function` by default unless broader scope is needed) - `python-backend/tests/conftest.py:23`, `python-backend/tests/conftest.py:29`, `python-backend/tests/conftest.py:40`, `python-backend/tests/conftest.py:65`, `python-backend/tests/conftest.py:74`
- [x] Reorganize tests into folders by domain (similar to existing `services/` organization):
  - [x] `python-backend/tests/api/` for API route tests - `python-backend/tests/api/test_health.py:1`, `python-backend/tests/api/test_items.py:1`, `python-backend/tests/api/test_processing.py:1`, `python-backend/tests/api/test_ws_processing.py:1`
  - [x] `python-backend/tests/db/` for DB/repository tests - `python-backend/tests/db/test_database.py:1`, `python-backend/tests/db/test_repositories.py:1`
  - [x] `python-backend/tests/providers/` for provider tests - `python-backend/tests/providers/test_ollama.py:1`
  - [x] `python-backend/tests/services/` for service tests (existing) - `python-backend/tests/services/test_embeddings.py:1`, `python-backend/tests/services/test_parsing.py:1`
  - [x] `python-backend/tests/workflows/` for workflow tests - `python-backend/tests/workflows/test_processing.py:1`
  - [x] `python-backend/tests/core/` for cross-cutting tests (e.g., exceptions) - `python-backend/tests/core/test_exceptions.py:1`
  - [x] Add `__init__.py` files only where needed for package-relative imports - `python-backend/tests/api/__init__.py:1`, `python-backend/tests/db/__init__.py:1`, `python-backend/tests/providers/__init__.py:1`, `python-backend/tests/workflows/__init__.py:1`, `python-backend/tests/core/__init__.py:1`, `python-backend/tests/fakes/__init__.py:1`

---

## Learning Report

_Generated: 2026-02-10_

### Summary

Backend processing test coverage gaps were closed by adding new parsing/workflow test modules, extending processing retry API tests, and reorganizing the backend test suite into domain folders with shared fixtures. Verification runs show all tests passing with strong coverage improvements on the targeted modules.

### Patterns and Decisions

- Consolidated shared fixture setup in `python-backend/tests/conftest.py` to reduce duplication and keep test setup consistent.
- Introduced `python-backend/tests/fakes/providers.py` as a reusable deterministic provider fake for service/workflow tests.
- Separated tests by domain (`api`, `db`, `providers`, `services`, `workflows`, `core`) to improve discoverability and reduce root-level test sprawl.
- Added an explicit `integration` marker in `python-backend/pyproject.toml` to categorize full workflow orchestration tests.

### Challenges and Solutions

- Workflow tests needed deterministic behavior across provider, chunking, extraction, and embedding boundaries.
  - Solution: patched `OllamaProvider` and workflow services with controlled mocks in `python-backend/tests/workflows/test_processing.py`.
- Fixture duplication across modules introduced drift risk.
  - Solution: moved fixture definitions into `python-backend/tests/conftest.py` and updated tests to consume shared fixtures.
- API retry edge cases required stable queue-state simulation.
  - Solution: reused the centralized `client` fixture with mocked `ProcessingQueue` behavior to assert API outcomes cleanly.

### Lessons Learned

- A dedicated `tests/fakes/` module significantly improves reuse and readability when multiple test modules need the same deterministic doubles.
- Domain-based test folder organization makes maintenance easier as the backend surface area grows.
- Integration marker hygiene in `pyproject.toml` helps teams selectively run heavier orchestration tests when needed.

### Documentation Impact

#### Developer Docs Review

### Scope Reviewed

- Code scope: task implementation (backend test coverage + backend test-suite reorganization)
- Docs reviewed: `docs/developer/quality-tooling/testing.md`, `docs/developer/python-backend/architecture.md`, `docs/developer/README.md`

### testing.md

**Status:** Needs Updates

#### Issues Found

- **Codebase Consistency:** `docs/developer/quality-tooling/testing.md:304` states `MockAIProvider` is defined in `tests/conftest.py`, but implementation is in `python-backend/tests/fakes/providers.py`.
  - **Fix:** Update the note to reference `tests/fakes/providers.py`.
- **Correctness:** `docs/developer/quality-tooling/testing.md:327` uses stale example path `tests/test_api_items.py`.
  - **Fix:** Update the example to `tests/api/test_items.py`.
- **Evergreenness:** `docs/developer/quality-tooling/testing.md:380` uses stale command `pytest tests/test_api_items.py`.
  - **Fix:** Update command to `pytest tests/api/test_items.py`.

---

### architecture.md

**Status:** Minor Issues

#### Issues Found

- **Completeness:** `docs/developer/python-backend/architecture.md:118` test tree does not currently mention `tests/fakes/`.
  - **Fix:** Add `tests/fakes/` entry (or a note that shared test doubles live there).

---

### README.md

**Status:** Good

#### Issues Found

- No issues found.

---

### Summary by Criterion

| Criterion            | Total Issues |
| -------------------- | ------------ |
| Correctness          | 1            |
| Codebase Consistency | 1            |
| Evergreenness        | 1            |
| Completeness         | 1            |
| Quality              | 0            |

### Priority Recommendations

1. Update `docs/developer/quality-tooling/testing.md` to fix stale file-path references and `MockAIProvider` location.
2. Add `tests/fakes/` coverage to the backend test tree in `docs/developer/python-backend/architecture.md`.
3. Re-run `$docs-reviewer` after doc updates to confirm all backend testing docs are fully aligned.

#### Docs requiring updates

- `docs/developer/quality-tooling/testing.md` - path examples and fixture/fake location note are partially stale.
- `docs/developer/python-backend/architecture.md` - test tree can be made complete by documenting `tests/fakes/`.

#### Docs validated as accurate

- `docs/developer/README.md` still correctly indexes the relevant backend/testing documentation.
