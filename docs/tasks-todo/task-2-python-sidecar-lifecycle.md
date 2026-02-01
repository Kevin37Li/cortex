# Task: Implement Python Sidecar Lifecycle Management in Rust

## Summary

Implement the Rust-side process management for the Python backend sidecar: spawn the Python process on app launch, poll `/api/health` until ready, monitor health continuously, restart on crash, and cleanly shut down on app exit. This is the bridge that makes the Tauri app launch and manage the Python backend automatically.

## Acceptance Criteria

- [ ] Rust spawns Python backend as a child process on Tauri app startup
- [ ] Health polling: Rust polls `GET http://localhost:{port}/api/health` until it returns 200 or 503 (max 30s timeout)
- [ ] Continuous health monitoring: background task checks health every 5 seconds
- [ ] Crash recovery: if Python process exits or health check fails 3 consecutive times, Rust restarts it (max 3 restart attempts)
- [ ] Clean shutdown: on app exit, Rust sends SIGTERM to Python, waits 5s, then SIGKILL if needed
- [ ] Frontend receives sidecar status events via Tauri event system (`sidecar-status` event with `starting`, `ready`, `restarting`, `failed` states)
- [ ] Tauri command `get_sidecar_status` exposed for on-demand status check (with `#[specta::specta]`)
- [ ] `SidecarStatus` enum defined in `types.rs` with `#[derive(Type)]` for TypeScript binding generation
- [ ] Command registered in `bindings.rs` via `collect_commands![]`
- [ ] Run `bun run rust:bindings` to regenerate TypeScript bindings after adding Rust commands
- [ ] Unit tests for status transitions, restart count logic, and skip-sidecar flag
- [ ] `bun run check:all` passes

## Dependencies

- Phase 1 complete: Health check endpoint exists at `GET /api/health`
- Phase 1 complete: Tauri app shell with event system
- Reference: `docs/developer/architecture/python-sidecar.md` (startup/shutdown/crash recovery sequences)
- Reference: `docs/developer/core-systems/tauri-commands.md` (command pattern with tauri-specta)

## Technical Notes

### Process Spawning

- Python is started via `uv run python -m src.main` from the `python-backend/` working directory (matches existing `python:dev` script pattern — do NOT use `--reload` for production sidecar)
- Use `tokio::process::Command` for async process spawning
- The sidecar should NOT be spawned during tests or development mode when the backend is run separately
- Add environment variable `CORTEX_SKIP_SIDECAR=true` to disable auto-spawn (follows `CORTEX_` env prefix convention)

### Port Configuration

- Default port is `8742`, but the Python backend reads `CORTEX_PORT` via pydantic-settings
- The Rust sidecar must read the same `CORTEX_PORT` env var (falling back to `8742`) so the health poll targets the correct port

### Working Directory

- In development: `python-backend/` relative to the project root
- In production: resolve via `app.path().resource_dir()` or equivalent bundling strategy (see `docs/developer/python-backend/bundling.md` when available)

### Dependencies to Add

Add to `src-tauri/Cargo.toml` (neither is a direct dependency today):

```toml
reqwest = { version = "0.12", features = ["json"] }
tokio = { version = "1", features = ["process", "time", "sync"] }
```

### Health Check Logic

- The health endpoint returns **200** when `overall_status == "healthy"` and **503** when `"degraded"` (e.g., Ollama unavailable)
- Accept both 200 and 503 as "backend is running" — a 503 with `"degraded"` is still a functioning backend
- Only connection errors (no response at all) should count as health check failures

### Event-Driven Bridge

- Emit events using `app.emit("sidecar-status", payload)` per the event-driven bridge pattern
- Store the child process handle in Tauri's managed state using `Arc<Mutex<SidecarState>>`

### Tauri-Specta Command Pattern

- `get_sidecar_status` must use both `#[tauri::command]` and `#[specta::specta]` attributes
- Define `SidecarStatus` enum in `types.rs` with:

```rust
#[derive(Debug, Clone, Serialize, Deserialize, specta::Type)]
#[serde(rename_all = "lowercase")]
pub enum SidecarStatus {
    Starting,
    Ready,
    Restarting,
    Failed,
}
```

- Define managed state struct:

```rust
pub struct SidecarState {
    pub child: Option<tokio::process::Child>,
    pub status: SidecarStatus,
    pub restart_count: u32,
}
```

Wrap in `Arc<Mutex<SidecarState>>` and register via `app.manage(...)`.

## Startup Sequence

```
1. Tauri main process starts
2. Check CORTEX_SKIP_SIDECAR — if "true", skip steps 3-7
3. Rust spawns Python: `uv run python -m src.main` (cwd: python-backend/)
4. Emit event: sidecar-status = "starting"
5. Poll GET /api/health every 500ms (max 30s), accept 200 or 503
6. On success: emit sidecar-status = "ready"
7. On timeout: emit sidecar-status = "failed", show error dialog
8. Start background health monitor (every 5s)
```

## Shutdown Sequence

Uses Tauri v2's `.build()` + `.run()` pattern to intercept `RunEvent::Exit`:

```
1. App receives RunEvent::ExitRequested or RunEvent::Exit
2. Send SIGTERM to Python child process
3. Wait up to 5 seconds for exit
4. If still running, send SIGKILL
5. Tauri exits
```

**Note:** The current `lib.rs` uses `.run(context).expect(...)` which must be refactored to `.build(context)?.run(|_app, event| { ... })` to handle exit events. On macOS, closing all windows does NOT quit the app — `RunEvent::Exit` is the correct shutdown hook.

## Files to Create/Modify

**Create:**

- `src-tauri/src/sidecar.rs` — Sidecar lifecycle management module (spawn, health poll, monitor, shutdown)

**Modify:**

- `src-tauri/src/lib.rs` — Initialize sidecar on startup, register managed state, refactor to `.build()` + `.run()` pattern for shutdown handling
- `src-tauri/src/types.rs` — Add `SidecarStatus` enum with `#[derive(Type)]`
- `src-tauri/src/commands/mod.rs` — Add `pub mod sidecar;` (if command placed in `commands/sidecar.rs`) or import from top-level `sidecar.rs`
- `src-tauri/src/bindings.rs` — Register `get_sidecar_status` in `collect_commands![]`
- `src-tauri/Cargo.toml` — Add `reqwest` and `tokio` as direct dependencies

**After implementation:**

- Run `bun run rust:bindings` to regenerate `src/lib/tauri-bindings.ts`
- Run `bun run check:all` to verify quality gates

## Verification

```bash
# Build Tauri backend
cd src-tauri && cargo build

# Run unit tests
cd src-tauri && cargo test

# Regenerate bindings
bun run rust:bindings

# Quality gates
bun run check:all

# Manual test: launch app, verify Python backend starts
# Check console for sidecar status events
# Test CORTEX_SKIP_SIDECAR=true skips spawning
# Test closing app cleanly shuts down Python process
```

## Future Considerations

- CSP update: When frontend tasks (12-17) add direct API calls to the Python backend, `http://localhost:8742` and `ws://localhost:8742` must be added to `connect-src` in `tauri.conf.json`
- Production bundling: The working directory resolution for `python-backend/` in production builds needs a bundling strategy

---

## Implementation Details

_Tracked: 2025-01-31_

### Files Changed

| File | Change | Description |
| ---- | ------ | ----------- |
| `src-tauri/src/sidecar.rs` | Created | Core sidecar lifecycle module: spawn, health polling, monitoring, crash recovery, shutdown |
| `src-tauri/src/commands/sidecar.rs` | Created | Tauri command `get_sidecar_status` with specta bindings |
| `src-tauri/src/types.rs` | Modified | Added `SidecarStatus` enum with `#[derive(Type)]`, `SidecarState` struct, and constants |
| `src-tauri/src/lib.rs` | Modified | Initialize sidecar state, call `initialize_sidecar()` in setup, handle `RunEvent::Exit` for shutdown |
| `src-tauri/src/commands/mod.rs` | Modified | Added `pub mod sidecar;` export |
| `src-tauri/src/bindings.rs` | Modified | Registered `sidecar::get_sidecar_status` in `collect_commands![]` |
| `src-tauri/Cargo.toml` | Modified | Added `reqwest`, `tokio` (with process/time/sync features), and `libc` (unix-only) |
| `src-tauri/Cargo.lock` | Modified | Lock file updated with new dependencies |
| `src/lib/bindings.ts` | Modified | Auto-generated TypeScript bindings including `SidecarStatus` type and `getSidecarStatus` command |

### Dependencies Added

- `reqwest@0.12` (features: `json`) - HTTP client for health checks
- `tokio@1` (features: `process`, `time`, `sync`) - Async process spawning, timers, and Mutex
- `libc@0.2` (unix-only) - For SIGTERM signal handling on graceful shutdown

### Acceptance Criteria Status

- [x] Rust spawns Python backend as a child process on Tauri app startup - Implemented in `sidecar.rs:61-74` (`spawn_python_process`)
- [x] Health polling: Rust polls `GET http://localhost:{port}/api/health` until it returns 200 or 503 (max 30s timeout) - Implemented in `sidecar.rs:80-111` (`poll_health_until_ready`)
- [x] Continuous health monitoring: background task checks health every 5 seconds - Implemented in `sidecar.rs:204-319` (`start_health_monitor`)
- [x] Crash recovery: if Python process exits or health check fails 3 consecutive times, Rust restarts it (max 3 restart attempts) - Implemented in `sidecar.rs:251-318`
- [x] Clean shutdown: on app exit, Rust sends SIGTERM to Python, waits 5s, then SIGKILL if needed - Implemented in `sidecar.rs:325-381` (`shutdown_sidecar`)
- [x] Frontend receives sidecar status events via Tauri event system (`sidecar-status` event with `starting`, `ready`, `restarting`, `failed` states) - Implemented in `sidecar.rs:128-138` (`emit_status`)
- [x] Tauri command `get_sidecar_status` exposed for on-demand status check (with `#[specta::specta]`) - Implemented in `commands/sidecar.rs:13-20`
- [x] `SidecarStatus` enum defined in `types.rs` with `#[derive(Type)]` for TypeScript binding generation - Implemented in `types.rs:131-138`
- [x] Command registered in `bindings.rs` via `collect_commands![]` - Implemented in `bindings.rs:19`
- [x] Run `bun run rust:bindings` to regenerate TypeScript bindings after adding Rust commands - Bindings regenerated in `src/lib/bindings.ts:149-156`
- [x] Unit tests for status transitions, restart count logic, and skip-sidecar flag - Implemented in `sidecar.rs:383-515` (14 tests)
- [x] `bun run check:all` passes - Verified (all 39 JS tests, 16 Rust tests, 135 Python tests pass)

---

## Learning Report

_Generated: 2025-01-31_

### Summary

Implemented complete Python sidecar lifecycle management in Rust for the Tauri application. The implementation enables automatic spawning of the Python FastAPI backend when the app launches, with health polling, continuous monitoring, crash recovery (up to 3 restarts), and graceful shutdown via SIGTERM/SIGKILL. Added 14 unit tests covering environment variable handling, status serialization, and restart logic. All 190 tests across the stack pass.

**Key metrics:**
- 2 new Rust files created (~500 lines of code)
- 5 existing Rust files modified
- 3 new dependencies added (reqwest, tokio features, libc)
- 14 new unit tests
- TypeScript bindings auto-generated

### Patterns & Decisions

**1. Async state management with `Arc<Mutex<SidecarState>>`**
Used Tauri's managed state system with `Arc<Mutex<SidecarState>>` to share the sidecar state between the setup hook, the async health monitor task, and the Tauri command. The state holds the child process handle, current status, and restart count.

**2. Event-driven status updates**
Following the documented event-driven bridge pattern, status changes are emitted via `app.emit("sidecar-status", &status)`. The `emit_status` helper updates both managed state and emits the event in one call, ensuring consistency.

**3. Tauri v2 `.build()` + `.run()` pattern**
Refactored `lib.rs` to use `.build(context)?.run(|app, event| ...)` instead of `.run(context).expect(...)` to intercept `RunEvent::Exit` for shutdown handling. This matches the documented shutdown sequence requirement.

**4. Health check tolerance**
Both HTTP 200 and 503 responses count as "backend is running" - only connection errors trigger failure counts. This matches the spec: a 503 with `"degraded"` status (e.g., Ollama unavailable) is still a functioning backend.

**5. Platform-specific shutdown**
Used conditional compilation (`#[cfg(unix)]`) for SIGTERM handling on Unix platforms, with a fallback to `child.kill()` on other platforms. Required adding `libc` as a unix-only dependency.

**6. Module organization**
Split implementation into:
- `sidecar.rs` - Core lifecycle logic (spawn, poll, monitor, shutdown)
- `commands/sidecar.rs` - Tauri command wrapper for frontend access
- `types.rs` - Shared types (`SidecarStatus`, `SidecarState`, constants)

### Challenges & Solutions

**1. Async task spawning from sync setup hook**
The Tauri setup hook is sync, but sidecar operations are async. Solution: Use `tauri::async_runtime::spawn()` to launch the async lifecycle task from the sync context.

**2. State sharing between setup and RunEvent handler**
Needed the same `Arc<Mutex<SidecarState>>` in both setup (for initialization) and the run event handler (for shutdown). Solution: Clone the Arc before `.manage()` and capture the clone in the `.run()` closure.

**3. Graceful shutdown with timeout**
Required sending SIGTERM, waiting with timeout, then SIGKILL. Solution: Use `tokio::time::timeout(SHUTDOWN_TIMEOUT, child.wait())` wrapped in the async runtime block.

**4. Test isolation for env var tests**
Multiple tests modify the same environment variables and run in parallel. Solution: Use a `Mutex<()>` guard (`ENV_LOCK`) to serialize env-var-dependent tests.

### Lessons Learned

**What worked well:**
- The task spec was thorough with clear acceptance criteria and code snippets
- Having the documented patterns (event-driven bridge, tauri-specta) made integration straightforward
- Separating the command layer from the lifecycle module kept code clean
- Unit tests for pure logic (port parsing, skip flag, serialization) were easy to write and valuable

**What could be improved:**
- Integration tests for the full lifecycle would catch spawn/health failures
- The health monitor loop continues on failed status - could add exponential backoff
- No logging for health check success during monitoring (only failures)

**Recommendations for similar tasks:**
- When adding Tauri commands with managed state, define the state struct and command in separate modules to avoid circular dependencies
- Use `kill_on_drop(true)` on child processes to ensure cleanup even on panic
- Test serialization roundtrips for any enum exposed to TypeScript

### Documentation Impact

**Existing docs that are accurate:**
- `docs/developer/architecture/python-sidecar.md` - Sequences and patterns are correctly implemented
- `docs/developer/core-systems/tauri-commands.md` - Command pattern with specta worked as documented

**Potential updates:**
- `docs/developer/architecture/python-sidecar.md` could add a note about the `libc` dependency for Unix shutdown
- Consider adding `CORTEX_SKIP_SIDECAR` to a developer environment variables reference doc

**No new documentation required** - implementation follows existing patterns.
