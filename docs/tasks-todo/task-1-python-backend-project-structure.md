# Task: Initialize Python Backend Project Structure

## Summary

Set up the FastAPI project with proper layering following documented architecture patterns.

## Acceptance Criteria

- [ ] Python project created in `python/` directory
- [ ] FastAPI application initialized with proper folder structure:
  - `python/app/` - main application package
  - `python/app/api/` - API routes
  - `python/app/core/` - core utilities (config, logging)
  - `python/app/db/` - database layer
  - `python/app/models/` - Pydantic models
  - `python/app/services/` - business logic
- [ ] `pyproject.toml` with dependencies (FastAPI, uvicorn, pydantic, python-dotenv)
- [ ] Entry point `python/app/main.py` with basic FastAPI app
- [ ] Development server runs on `localhost:8742`
- [ ] `.python-version` file specifying Python 3.11+

## Dependencies

- None (first task)

## Technical Notes

- Follow patterns in `docs/developer/python-backend/architecture.md`
- Use `uv` for dependency management (fast, modern)
- Port 8742 specified in MVP plan architecture diagram
- Localhost-only binding for security

## Files to Create

```
python/
├── .python-version
├── pyproject.toml
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   └── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── db/
│   │   └── __init__.py
│   ├── models/
│   │   └── __init__.py
│   └── services/
│       └── __init__.py
```

## Verification

```bash
cd python && uv run uvicorn app.main:app --host 127.0.0.1 --port 8742
# Should start server and respond to http://localhost:8742/
```
