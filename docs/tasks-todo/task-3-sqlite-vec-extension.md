# Task: Install and Configure sqlite-vec Extension

## Summary
Add sqlite-vec extension for vector similarity search capabilities in SQLite.

## Acceptance Criteria
- [ ] sqlite-vec Python package added to dependencies
- [ ] Extension loading integrated into database initialization
- [ ] Verification that vector functions are available after load
- [ ] Helper utilities for common vector operations:
  - Creating vector columns
  - Inserting vectors
  - Similarity search query builder
- [ ] Unit tests verifying extension functionality

## Dependencies
- Task 2: SQLite database connection

## Technical Notes
- Use `sqlite-vec` package from PyPI
- Extension must be loaded on each connection
- Vector dimensions will be determined by embedding model (typically 384-1536)
- See sqlite-vec documentation for function signatures

## Phase
Phase 1: Foundation
