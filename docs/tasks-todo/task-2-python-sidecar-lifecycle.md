# Task: Implement Python Sidecar Lifecycle Management in Rust

## Summary

Implement the Rust-side process management for the Python backend sidecar: spawn the Python process on app launch, poll `/api/health` until ready, monitor health continuously, restart on crash, and cleanly shut down on app exit. This is the bridge that makes the Tauri app launch and manage the Python backend automatically.

## Acceptance Criteria

- [ ] Rust spawns Python backend as a child process on Tauri app startup
- [ ] Health polling: Rust polls `GET http://localhost:8742/api/health` until it returns 200 (max 30s timeout)
- [ ] Continuous health monitoring: background task checks health every 5 seconds
- [ ] Crash recovery: if Python process exits or health check fails 3 consecutive times, Rust restarts it (max 3 restart attempts)
- [ ] Clean shutdown: on app close, Rust sends SIGTERM to Python, waits 5s, then SIGKILL if needed
- [ ] Frontend receives sidecar status events via Tauri event system (`sidecar-status` event with `starting`, `ready`, `restarting`, `failed` states)
- [ ] Tauri command `get_sidecar_status` exposed for on-demand status check
- [ ] Run `bun run rust:bindings` to regenerate TypeScript bindings after adding Rust commands

## Dependencies

- Phase 1 complete: Health check endpoint exists at `GET /api/health`
- Phase 1 complete: Tauri app shell with event system
- Reference: `docs/developer/architecture/python-sidecar.md` (startup/shutdown/crash recovery sequences)

## Technical Notes

- Python is started via `uv run uvicorn src.main:app --host 127.0.0.1 --port 8742` (or equivalent command from `python-backend/`)
- Use `tokio::process::Command` for async process spawning
- Use `reqwest` for health polling (already a Tauri dependency)
- Emit events using `app.emit("sidecar-status", payload)` per the event-driven bridge pattern
- Store the child process handle in Tauri's managed state
- The sidecar should NOT be spawned during tests or development mode when the backend is run separately
- Add a config flag or environment variable `CORTEX_SKIP_SIDECAR=true` to disable auto-spawn

## Startup Sequence

```
1. Tauri main process starts
2. Rust spawns Python: `uv run uvicorn src.main:app --host 127.0.0.1 --port 8742`
3. Emit event: sidecar-status = "starting"
4. Poll GET /api/health every 500ms (max 30s)
5. On 200 response: emit sidecar-status = "ready"
6. On timeout: emit sidecar-status = "failed", show error dialog
7. Start background health monitor (every 5s)
```

## Shutdown Sequence

```
1. Tauri on_window_event(CloseRequested)
2. Send SIGTERM to Python child process
3. Wait up to 5 seconds for exit
4. If still running, send SIGKILL
5. Tauri exits
```

## Files to Create/Modify

**Create:**

- `src-tauri/src/sidecar.rs` — Sidecar lifecycle management module

**Modify:**

- `src-tauri/src/main.rs` (or `lib.rs`) — Initialize sidecar on startup, register command, handle shutdown
- `src-tauri/Cargo.toml` — Add `reqwest` if not present (for health polling)

**After implementation:**

- Run `bun run rust:bindings` to regenerate `src/lib/tauri-bindings.ts`

## Verification

```bash
# Build Tauri backend
cd src-tauri && cargo build

# Regenerate bindings
bun run rust:bindings

# Manual test: launch app, verify Python backend starts
# Check console for sidecar status events
```
