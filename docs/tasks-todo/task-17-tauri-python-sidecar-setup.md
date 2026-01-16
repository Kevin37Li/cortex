# Task: Configure Tauri to Launch Python Backend as Sidecar

## Summary
Set up Tauri to automatically start and manage the Python backend process.

## Acceptance Criteria
- [ ] Python backend packaged/bundled with Tauri app
- [ ] Backend starts automatically when app launches
- [ ] Backend shuts down when app closes
- [ ] Startup waits for backend health check before showing main UI
- [ ] Error handling if backend fails to start
- [ ] Logging of backend stdout/stderr for debugging
- [ ] Configuration for development vs production paths

## Dependencies
- Task 1: Python backend project structure
- Task 7: Health check endpoint

## Technical Notes
- Use Tauri's sidecar/shell plugin for process management
- See `docs/developer/architecture/python-sidecar.md` for patterns
- Development: run backend from source with uvicorn
- Production: bundled Python executable or virtual environment
- Consider port conflict detection and handling

## Phase
Phase 1: Foundation
