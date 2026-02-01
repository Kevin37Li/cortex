//! Sidecar status command.
//!
//! Provides a Tauri command for the frontend to query the current
//! status of the Python backend sidecar process.

use std::sync::Arc;

use tokio::sync::Mutex;

use crate::types::{SidecarState, SidecarStatus};

/// Returns the current status of the Python sidecar process.
#[tauri::command]
#[specta::specta]
pub async fn get_sidecar_status(
    state: tauri::State<'_, Arc<Mutex<SidecarState>>>,
) -> Result<SidecarStatus, String> {
    let s = state.lock().await;
    Ok(s.status.clone())
}
