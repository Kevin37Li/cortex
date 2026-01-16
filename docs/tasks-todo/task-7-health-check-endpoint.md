# Task: Create Health Check Endpoint

## Summary
Implement `/api/health` endpoint for backend health monitoring.

## Acceptance Criteria
- [ ] `GET /api/health` endpoint returning:
  ```json
  {
    "status": "healthy",
    "version": "0.1.0",
    "database": "connected",
    "timestamp": "2026-01-16T12:00:00Z"
  }
  ```
- [ ] Database connectivity check (simple query)
- [ ] Returns 503 if database is unreachable
- [ ] Response model with Pydantic
- [ ] Unit tests for health endpoint

## Dependencies
- Task 2: SQLite database connection

## Technical Notes
- This endpoint is used by Tauri frontend to verify backend is running
- Keep response fast (<100ms)
- Consider adding version from pyproject.toml

## Phase
Phase 1: Foundation
