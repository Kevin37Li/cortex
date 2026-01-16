# Task: Create SQLite Database Connection and Configuration

## Summary
Set up SQLite database connection infrastructure with async support and configuration management.

## Acceptance Criteria
- [ ] Database configuration in `core/config.py` with settings for:
  - Database file path (default: `~/.cortex/cortex.db`)
  - Connection pool settings
- [ ] Database connection manager that:
  - Creates database file and parent directories if missing
  - Provides async connection context manager
  - Handles connection lifecycle properly
- [ ] Database initialization function that runs on app startup
- [ ] Unit tests for database connection

## Dependencies
- Task 1: Python backend project structure

## Technical Notes
- Use `aiosqlite` for async SQLite operations
- Store database in user data directory, not project directory
- Enable WAL mode for better concurrent read performance
- Consider using `databases` package for async ORM-like interface

## Phase
Phase 1: Foundation
