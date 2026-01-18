# Task: Initialize Python Backend Project Structure

## Summary

Set up the FastAPI project with proper layering following documented architecture patterns.

## Acceptance Criteria

- [ ] Python project created in `python-backend/` directory
- [ ] FastAPI application initialized with proper folder structure:
  - `python-backend/src/` - main application package
  - `python-backend/src/api/` - API routes
  - `python-backend/src/db/` - database layer
  - `python-backend/src/db/repositories/` - repository classes
  - `python-backend/src/providers/` - AI provider abstractions
  - `python-backend/src/workflows/` - LangGraph workflows (empty for Phase 1)
  - `python-backend/src/services/` - business logic
- [ ] `pyproject.toml` with dependencies (FastAPI, uvicorn, pydantic, pydantic-settings, python-dotenv, aiosqlite)
- [ ] Entry point `python-backend/src/main.py` with basic FastAPI app
- [ ] Development server runs on `localhost:8742`
- [ ] `.python-version` file specifying Python 3.11+
- [ ] CORS middleware configured for Tauri webview

## Dependencies

- None (first task)

## Technical Notes

- Follow patterns in `docs/developer/python-backend/architecture.md`
- Use `uv` for dependency management (fast, modern)
- Port 8742 specified in MVP plan architecture diagram
- Localhost-only binding for security

## Files to Create

```
python-backend/
├── .python-version
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   └── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── repositories/
│   │       └── __init__.py
│   ├── providers/
│   │   └── __init__.py
│   ├── workflows/
│   │   └── __init__.py
│   └── services/
│       └── __init__.py
└── tests/
    └── __init__.py
```

## Verification

```bash
cd python-backend && uv run uvicorn src.main:app --host 127.0.0.1 --port 8742
# Should start server and respond to http://localhost:8742/
```
