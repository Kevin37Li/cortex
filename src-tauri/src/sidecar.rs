//! Python sidecar lifecycle management.
//!
//! Manages spawning, health polling, continuous monitoring, crash recovery,
//! and clean shutdown of the Python backend process.

use std::sync::Arc;
use std::time::Duration;

use tokio::process::Command;
use tokio::sync::Mutex;

use tauri::{AppHandle, Emitter, Manager};

use crate::types::{SidecarState, SidecarStatus, DEFAULT_SIDECAR_PORT, MAX_RESTART_ATTEMPTS};

/// Environment variable to skip sidecar spawning (for tests/development).
const SKIP_SIDECAR_ENV: &str = "CORTEX_SKIP_SIDECAR";

/// Environment variable for the Python backend port.
const PORT_ENV: &str = "CORTEX_PORT";

/// Health poll interval during startup.
const STARTUP_POLL_INTERVAL: Duration = Duration::from_millis(500);

/// Maximum time to wait for the sidecar to become healthy during startup.
const STARTUP_TIMEOUT: Duration = Duration::from_secs(30);

/// Health check interval during continuous monitoring.
const MONITOR_INTERVAL: Duration = Duration::from_secs(5);

/// Number of consecutive health check failures before triggering restart.
const FAILURE_THRESHOLD: u32 = 3;

/// Time to wait for graceful shutdown before sending SIGKILL.
const SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(5);

/// Health check request timeout.
const HEALTH_REQUEST_TIMEOUT: Duration = Duration::from_secs(2);

/// Returns the configured sidecar port, reading from `CORTEX_PORT` env var
/// and falling back to [`DEFAULT_SIDECAR_PORT`].
fn sidecar_port() -> u16 {
    std::env::var(PORT_ENV)
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_SIDECAR_PORT)
}

/// Returns `true` if sidecar spawning should be skipped
/// (when `CORTEX_SKIP_SIDECAR=true`).
pub fn should_skip_sidecar() -> bool {
    std::env::var(SKIP_SIDECAR_ENV)
        .map(|v| v.eq_ignore_ascii_case("true") || v == "1")
        .unwrap_or(false)
}

/// Spawns the Python backend as a child process.
///
/// Runs `uv run python -m src.main` from the `python-backend/` working directory.
/// Returns the child process handle on success.
fn spawn_python_process() -> Result<tokio::process::Child, String> {
    let working_dir = std::env::current_dir()
        .map(|d| d.join("python-backend"))
        .map_err(|e| format!("Failed to resolve working directory: {e}"))?;

    log::info!("Spawning Python sidecar from {}", working_dir.display());

    Command::new("uv")
        .args(["run", "python", "-m", "src.main"])
        .current_dir(&working_dir)
        .kill_on_drop(true)
        .spawn()
        .map_err(|e| format!("Failed to spawn Python sidecar: {e}"))
}

/// Polls the health endpoint until the backend responds (200 or 503)
/// or the timeout is reached.
///
/// Returns `Ok(())` if the backend becomes reachable, `Err` on timeout.
async fn poll_health_until_ready() -> Result<(), String> {
    let port = sidecar_port();
    let url = format!("http://localhost:{port}/api/health");
    let client = reqwest::Client::builder()
        .timeout(HEALTH_REQUEST_TIMEOUT)
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {e}"))?;

    let deadline = tokio::time::Instant::now() + STARTUP_TIMEOUT;

    loop {
        match client.get(&url).send().await {
            Ok(resp) => {
                let status = resp.status();
                if status.as_u16() == 200 || status.as_u16() == 503 {
                    log::info!("Python backend is reachable (HTTP {status})");
                    return Ok(());
                }
                log::debug!("Health check returned unexpected status: {status}");
            }
            Err(e) => {
                log::debug!("Health poll pending: {e}");
            }
        }

        if tokio::time::Instant::now() >= deadline {
            return Err("Python backend did not become ready within 30 seconds".to_string());
        }

        tokio::time::sleep(STARTUP_POLL_INTERVAL).await;
    }
}

/// Performs a single health check against the Python backend.
///
/// Returns `true` if the backend responds (200 or 503), `false` on connection error.
async fn check_health(client: &reqwest::Client, port: u16) -> bool {
    let url = format!("http://localhost:{port}/api/health");
    match client.get(&url).send().await {
        Ok(resp) => {
            let status = resp.status().as_u16();
            status == 200 || status == 503
        }
        Err(_) => false,
    }
}

/// Emits a `sidecar-status` event to the frontend and updates managed state.
async fn emit_status(app: &AppHandle, state: &Arc<Mutex<SidecarState>>, status: SidecarStatus) {
    // Update managed state asynchronously.
    {
        let mut s = state.lock().await;
        s.status = status.clone();
    }

    if let Err(e) = app.emit("sidecar-status", &status) {
        log::error!("Failed to emit sidecar-status event: {e}");
    }
}

/// Initializes and starts the sidecar lifecycle.
///
/// Called from Tauri's `setup` hook. This will:
/// 1. Check `CORTEX_SKIP_SIDECAR` — return early if set
/// 2. Spawn the Python process
/// 3. Emit `starting` status
/// 4. Poll health until ready or timeout
/// 5. Start background health monitoring
pub fn initialize_sidecar(app: &AppHandle) {
    if should_skip_sidecar() {
        log::info!("CORTEX_SKIP_SIDECAR is set — skipping sidecar spawn");
        return;
    }

    let state: tauri::State<Arc<Mutex<SidecarState>>> = app.state();
    let state = state.inner().clone();
    let app_handle = app.clone();

    tauri::async_runtime::spawn(async move {
        start_sidecar(&app_handle, &state).await;
    });
}

/// Spawns the sidecar, polls health, and starts monitoring.
async fn start_sidecar(app: &AppHandle, state: &Arc<Mutex<SidecarState>>) {
    // Spawn the Python process
    let child = match spawn_python_process() {
        Ok(child) => child,
        Err(e) => {
            log::error!("Failed to spawn Python sidecar: {e}");
            emit_status(app, state, SidecarStatus::Failed).await;
            return;
        }
    };

    // Store child process and set status to starting
    {
        let mut s = state.lock().await;
        s.child = Some(child);
        s.status = SidecarStatus::Starting;
    }
    emit_status(app, state, SidecarStatus::Starting).await;

    // Poll health endpoint until ready
    match poll_health_until_ready().await {
        Ok(()) => {
            log::info!("Python sidecar is ready");
            emit_status(app, state, SidecarStatus::Ready).await;
        }
        Err(e) => {
            log::error!("Sidecar startup failed: {e}");
            emit_status(app, state, SidecarStatus::Failed).await;
            return;
        }
    }

    // Start continuous health monitoring
    start_health_monitor(app.clone(), state.clone()).await;
}

/// Background health monitor loop.
///
/// Checks health every 5 seconds. After 3 consecutive failures, attempts
/// to restart the sidecar (up to [`MAX_RESTART_ATTEMPTS`] total).
async fn start_health_monitor(app: AppHandle, state: Arc<Mutex<SidecarState>>) {
    let port = sidecar_port();
    let client = match reqwest::Client::builder()
        .timeout(HEALTH_REQUEST_TIMEOUT)
        .build()
    {
        Ok(c) => c,
        Err(e) => {
            log::error!("Failed to create health monitor HTTP client: {e}");
            return;
        }
    };

    let mut consecutive_failures: u32 = 0;

    loop {
        tokio::time::sleep(MONITOR_INTERVAL).await;

        // Check if the child process has exited
        let process_exited = {
            let mut s = state.lock().await;
            if let Some(ref mut child) = s.child {
                matches!(child.try_wait(), Ok(Some(_)))
            } else {
                true
            }
        };

        let healthy = if process_exited {
            false
        } else {
            check_health(&client, port).await
        };

        if healthy {
            consecutive_failures = 0;
            // Ensure status is Ready if it was Restarting
            let current_status = {
                let s = state.lock().await;
                s.status.clone()
            };
            if matches!(current_status, SidecarStatus::Restarting) {
                emit_status(&app, &state, SidecarStatus::Ready).await;
            }
            continue;
        }

        consecutive_failures += 1;
        log::warn!(
            "Sidecar health check failed ({consecutive_failures}/{FAILURE_THRESHOLD} consecutive)"
        );

        if consecutive_failures < FAILURE_THRESHOLD {
            continue;
        }

        // Reset failure counter for restart attempt
        consecutive_failures = 0;

        let restart_count = {
            let s = state.lock().await;
            s.restart_count
        };

        if restart_count >= MAX_RESTART_ATTEMPTS {
            log::error!(
                "Sidecar has exceeded max restart attempts ({MAX_RESTART_ATTEMPTS}), giving up"
            );
            emit_status(&app, &state, SidecarStatus::Failed).await;
            return;
        }

        log::warn!(
            "Attempting sidecar restart ({}/{})",
            restart_count + 1,
            MAX_RESTART_ATTEMPTS
        );
        emit_status(&app, &state, SidecarStatus::Restarting).await;

        // Kill existing process if still running
        {
            let mut s = state.lock().await;
            if let Some(ref mut child) = s.child {
                let _ = child.kill().await;
            }
            s.child = None;
            s.restart_count += 1;
        }

        // Spawn new process
        match spawn_python_process() {
            Ok(child) => {
                {
                    let mut s = state.lock().await;
                    s.child = Some(child);
                }
                match poll_health_until_ready().await {
                    Ok(()) => {
                        log::info!("Sidecar restarted successfully");
                        emit_status(&app, &state, SidecarStatus::Ready).await;
                    }
                    Err(e) => {
                        log::error!("Sidecar restart failed during health poll: {e}");
                        emit_status(&app, &state, SidecarStatus::Failed).await;
                        // Loop continues — will try again after next failure threshold
                    }
                }
            }
            Err(e) => {
                log::error!("Failed to respawn sidecar: {e}");
                emit_status(&app, &state, SidecarStatus::Failed).await;
                // Loop continues — will try again after next failure threshold
            }
        }
    }
}

/// Shuts down the Python sidecar process gracefully.
///
/// Sends SIGTERM, waits up to 5 seconds, then sends SIGKILL if needed.
/// Called from the `RunEvent::Exit` handler.
pub async fn shutdown_sidecar(state: &Arc<Mutex<SidecarState>>) {
    let mut s = state.lock().await;
    let child = match s.child.take() {
        Some(child) => child,
        None => {
            log::debug!("No sidecar process to shut down");
            return;
        }
    };

    log::info!("Shutting down Python sidecar...");

    // On Unix, send SIGTERM via the child's id
    #[cfg(unix)]
    {
        use tokio::time::timeout;

        if let Some(pid) = child.id() {
            // Send SIGTERM
            unsafe {
                libc::kill(pid as libc::pid_t, libc::SIGTERM);
            }
            log::debug!("Sent SIGTERM to sidecar (PID {pid})");

            // Wait for graceful exit
            let mut child = child;
            match timeout(SHUTDOWN_TIMEOUT, child.wait()).await {
                Ok(Ok(status)) => {
                    log::info!("Sidecar exited gracefully: {status}");
                    return;
                }
                Ok(Err(e)) => {
                    log::warn!("Error waiting for sidecar exit: {e}");
                }
                Err(_) => {
                    log::warn!("Sidecar did not exit within 5s, sending SIGKILL");
                }
            }

            // Force kill
            let _ = child.kill().await;
            log::info!("Sidecar forcefully terminated");
        } else {
            log::warn!("Could not get sidecar PID for graceful shutdown");
            let mut child = child;
            let _ = child.kill().await;
        }
    }

    // On non-Unix, just kill the process
    #[cfg(not(unix))]
    {
        let mut child = child;
        let _ = child.kill().await;
        log::info!("Sidecar process terminated");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    /// Mutex to serialize env-var tests (tests run in parallel and share the process env).
    static ENV_LOCK: Mutex<()> = Mutex::new(());

    #[test]
    fn test_sidecar_port_default() {
        let _guard = ENV_LOCK.lock().unwrap();
        std::env::remove_var(PORT_ENV);
        assert_eq!(sidecar_port(), DEFAULT_SIDECAR_PORT);
    }

    #[test]
    fn test_sidecar_port_from_env() {
        let _guard = ENV_LOCK.lock().unwrap();
        std::env::set_var(PORT_ENV, "9999");
        assert_eq!(sidecar_port(), 9999);
        std::env::remove_var(PORT_ENV);
    }

    #[test]
    fn test_sidecar_port_invalid_env() {
        let _guard = ENV_LOCK.lock().unwrap();
        std::env::set_var(PORT_ENV, "not_a_number");
        assert_eq!(sidecar_port(), DEFAULT_SIDECAR_PORT);
        std::env::remove_var(PORT_ENV);
    }

    #[test]
    fn test_should_skip_sidecar_true() {
        let _guard = ENV_LOCK.lock().unwrap();
        std::env::set_var(SKIP_SIDECAR_ENV, "true");
        assert!(should_skip_sidecar());
        std::env::remove_var(SKIP_SIDECAR_ENV);
    }

    #[test]
    fn test_should_skip_sidecar_one() {
        let _guard = ENV_LOCK.lock().unwrap();
        std::env::set_var(SKIP_SIDECAR_ENV, "1");
        assert!(should_skip_sidecar());
        std::env::remove_var(SKIP_SIDECAR_ENV);
    }

    #[test]
    fn test_should_skip_sidecar_case_insensitive() {
        let _guard = ENV_LOCK.lock().unwrap();
        std::env::set_var(SKIP_SIDECAR_ENV, "TRUE");
        assert!(should_skip_sidecar());
        std::env::remove_var(SKIP_SIDECAR_ENV);
    }

    #[test]
    fn test_should_skip_sidecar_false() {
        let _guard = ENV_LOCK.lock().unwrap();
        std::env::set_var(SKIP_SIDECAR_ENV, "false");
        assert!(!should_skip_sidecar());
        std::env::remove_var(SKIP_SIDECAR_ENV);
    }

    #[test]
    fn test_should_skip_sidecar_unset() {
        let _guard = ENV_LOCK.lock().unwrap();
        std::env::remove_var(SKIP_SIDECAR_ENV);
        assert!(!should_skip_sidecar());
    }

    #[test]
    fn test_sidecar_state_initial() {
        let state = SidecarState {
            child: None,
            status: SidecarStatus::Starting,
            restart_count: 0,
        };
        assert!(state.child.is_none());
        assert_eq!(state.restart_count, 0);
        assert!(matches!(state.status, SidecarStatus::Starting));
    }

    #[test]
    fn test_status_serialization() {
        let status = SidecarStatus::Ready;
        let json = serde_json::to_string(&status).unwrap();
        assert_eq!(json, "\"ready\"");

        let status = SidecarStatus::Starting;
        let json = serde_json::to_string(&status).unwrap();
        assert_eq!(json, "\"starting\"");

        let status = SidecarStatus::Restarting;
        let json = serde_json::to_string(&status).unwrap();
        assert_eq!(json, "\"restarting\"");

        let status = SidecarStatus::Failed;
        let json = serde_json::to_string(&status).unwrap();
        assert_eq!(json, "\"failed\"");
    }

    #[test]
    fn test_status_deserialization() {
        let status: SidecarStatus = serde_json::from_str("\"ready\"").unwrap();
        assert!(matches!(status, SidecarStatus::Ready));

        let status: SidecarStatus = serde_json::from_str("\"failed\"").unwrap();
        assert!(matches!(status, SidecarStatus::Failed));
    }

    #[test]
    fn test_restart_count_logic() {
        let mut restart_count: u32 = 0;

        // First restart
        assert!(restart_count < MAX_RESTART_ATTEMPTS);
        restart_count += 1;
        assert_eq!(restart_count, 1);

        // Second restart
        assert!(restart_count < MAX_RESTART_ATTEMPTS);
        restart_count += 1;
        assert_eq!(restart_count, 2);

        // Third restart
        assert!(restart_count < MAX_RESTART_ATTEMPTS);
        restart_count += 1;
        assert_eq!(restart_count, 3);

        // Should not restart again
        assert!(restart_count >= MAX_RESTART_ATTEMPTS);
    }
}
