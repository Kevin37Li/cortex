# Task: Implement Health Check Endpoint

## Summary

Create health check endpoints for backend status monitoring and frontend connectivity verification.

## Acceptance Criteria

- [ ] `GET /api/health` - Basic health check (always responds if server is running)
- [ ] Response includes:
  - `status`: "healthy" | "degraded" | "unhealthy"
  - `version`: Application version
  - `timestamp`: Current server time
  - `checks`: Object with component statuses
- [ ] Database connectivity check
- [ ] Response time < 100ms for basic health

## Dependencies

- Task 1: Python backend project structure
- Task 2: SQLite schema setup

## Technical Notes

- Health endpoint should be fast and lightweight
- Database check: simple query like `SELECT 1`
- Used by Tauri frontend to verify backend is ready
- Consider separate `/api/health/ready` for deep checks

## API Specification

```python
# Basic health check
GET /api/health
Response: 200 OK
{
    "status": "healthy",
    "version": "0.1.0",
    "timestamp": "2026-01-16T12:00:00Z",
    "checks": {
        "database": {
            "status": "healthy",
            "latency_ms": 2
        }
    }
}

# If database fails
Response: 503 Service Unavailable
{
    "status": "unhealthy",
    "version": "0.1.0",
    "timestamp": "2026-01-16T12:00:00Z",
    "checks": {
        "database": {
            "status": "unhealthy",
            "error": "Connection failed"
        }
    }
}
```

## Files to Create/Modify

- `python/app/api/routes/health.py` - Health endpoints
- `python/app/core/config.py` - Add version from pyproject.toml
- `python/app/main.py` - Register health routes

## Verification

```bash
# Check health
curl http://localhost:8742/api/health

# Verify database check works
# (should return healthy status with db latency)
```
