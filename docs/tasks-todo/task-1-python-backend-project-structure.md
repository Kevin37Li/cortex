# Task: Initialize Python Backend Project Structure

## Summary
Create the foundational FastAPI project structure with proper layering for the Cortex backend.

## Acceptance Criteria
- [ ] Python project initialized with `uv` package manager
- [ ] `pyproject.toml` with project metadata and dependencies (FastAPI, uvicorn, pydantic)
- [ ] Directory structure following layered architecture:
  ```
  backend/
  ├── src/
  │   └── cortex/
  │       ├── __init__.py
  │       ├── main.py          # FastAPI app entry
  │       ├── api/             # Route handlers
  │       │   └── __init__.py
  │       ├── core/            # Config, settings
  │       │   └── __init__.py
  │       ├── models/          # Pydantic models
  │       │   └── __init__.py
  │       ├── repositories/    # Data access layer
  │       │   └── __init__.py
  │       └── services/        # Business logic
  │           └── __init__.py
  ├── tests/
  │   └── __init__.py
  └── pyproject.toml
  ```
- [ ] Basic FastAPI app that starts and responds on localhost:8742
- [ ] Development scripts in pyproject.toml (dev server, lint, test)
- [ ] Ruff configured for linting/formatting

## Dependencies
- None (first task)

## Technical Notes
- Use Python 3.12+
- Port 8742 is specified in architecture docs
- Follow patterns in `docs/developer/python-backend/architecture.md`

## Phase
Phase 1: Foundation
