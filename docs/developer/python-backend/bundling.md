# Python Bundling

Packaging the Python backend for distribution with the Tauri app.

## Overview

The Python backend must be bundled as a standalone executable that:

- Runs without requiring Python to be installed
- Includes all dependencies (FastAPI, LangGraph, etc.)
- Works on macOS, Windows, and Linux
- Integrates with Tauri's sidecar system

## Bundling Options

| Tool            | Pros                          | Cons                  | Recommendation  |
| --------------- | ----------------------------- | --------------------- | --------------- |
| **PyInstaller** | Mature, well-documented       | Large binaries        | Primary choice  |
| **PyOxidizer**  | Rust-native, smaller binaries | Complex configuration | Alternative     |
| **Nuitka**      | Compiles to C, fast           | Long build times      | Not recommended |
| **cx_Freeze**   | Simple                        | Less maintained       | Not recommended |

**Recommendation**: Use PyInstaller for initial development, consider PyOxidizer for production builds.

## PyInstaller Setup

### Installation

```bash
pip install pyinstaller
```

### Basic Spec File

```python
# cortex-backend.spec
# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# Collect all source files
a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[
        # Include sqlite-vec extension
        ('path/to/vec0.dylib', '.'),  # macOS
        # ('path/to/vec0.dll', '.'),  # Windows
        # ('path/to/vec0.so', '.'),   # Linux
    ],
    datas=[
        # Include any data files
        ('src/db/migrations', 'db/migrations'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        # LangGraph imports
        'langgraph',
        'langchain',
        # Add other hidden imports as discovered
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='cortex-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for production
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### Build Commands

```bash
# Development build (faster, larger)
pyinstaller cortex-backend.spec --noconfirm

# Production build (optimized)
pyinstaller cortex-backend.spec --noconfirm --clean
```

### Output Structure

```
dist/
└── cortex-backend           # Single executable (macOS/Linux)
    # or
└── cortex-backend.exe       # Single executable (Windows)
```

## Platform-Specific Considerations

### macOS

```python
# In spec file
exe = EXE(
    ...
    target_arch='universal2',  # Build for both Intel and Apple Silicon
    codesign_identity='Developer ID Application: ...',  # For notarization
    entitlements_file='entitlements.plist',
)
```

**Entitlements** (entitlements.plist):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
</dict>
</plist>
```

### Windows

```python
# In spec file
exe = EXE(
    ...
    icon='assets/icon.ico',
    version='version_info.txt',
)
```

**Version info** (version_info.txt):

```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    ...
  ),
  ...
)
```

### Linux

```python
# In spec file - no special configuration needed
exe = EXE(
    ...
    strip=True,  # Strip debug symbols
)
```

## Tauri Sidecar Integration

### Tauri Configuration

```json
// tauri.conf.json
{
  "bundle": {
    "externalBin": ["binaries/cortex-backend"]
  }
}
```

### Binary Naming Convention

Tauri expects platform-specific naming:

```
binaries/
├── cortex-backend-aarch64-apple-darwin      # macOS ARM
├── cortex-backend-x86_64-apple-darwin       # macOS Intel
├── cortex-backend-x86_64-pc-windows-msvc.exe # Windows
└── cortex-backend-x86_64-unknown-linux-gnu  # Linux
```

### Rust Sidecar Management

```rust
// src-tauri/src/sidecar.rs
use tauri::api::process::{Command, CommandEvent};
use std::sync::Mutex;

pub struct SidecarState {
    child: Mutex<Option<tauri::api::process::CommandChild>>,
}

pub fn start_sidecar(app: &tauri::AppHandle) -> Result<(), String> {
    let (mut rx, child) = Command::new_sidecar("cortex-backend")
        .expect("Failed to create sidecar command")
        .args(["--port", "8742"])
        .spawn()
        .expect("Failed to spawn sidecar");

    // Store child process handle
    let state = app.state::<SidecarState>();
    *state.child.lock().unwrap() = Some(child);

    // Handle sidecar output
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    println!("[backend] {}", line);
                }
                CommandEvent::Stderr(line) => {
                    eprintln!("[backend error] {}", line);
                }
                CommandEvent::Error(err) => {
                    eprintln!("[backend fatal] {}", err);
                }
                CommandEvent::Terminated(payload) => {
                    println!("[backend] terminated: {:?}", payload);
                }
                _ => {}
            }
        }
    });

    Ok(())
}

pub fn stop_sidecar(app: &tauri::AppHandle) {
    let state = app.state::<SidecarState>();
    if let Some(child) = state.child.lock().unwrap().take() {
        child.kill().ok();
    }
}
```

### Lifecycle Management

```rust
// src-tauri/src/main.rs
fn main() {
    tauri::Builder::default()
        .manage(SidecarState { child: Mutex::new(None) })
        .setup(|app| {
            // Start backend on app launch
            start_sidecar(&app.handle())?;

            // Wait for backend to be ready
            let client = reqwest::blocking::Client::new();
            for _ in 0..30 {
                if client.get("http://localhost:8742/api/health").send().is_ok() {
                    break;
                }
                std::thread::sleep(std::time::Duration::from_millis(100));
            }

            Ok(())
        })
        .on_window_event(|event| {
            if let tauri::WindowEvent::Destroyed = event.event() {
                stop_sidecar(&event.window().app_handle());
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

## Build Pipeline

### CI/CD Script

```yaml
# .github/workflows/build.yml
jobs:
  build-backend:
    strategy:
      matrix:
        include:
          - os: macos-latest
            target: aarch64-apple-darwin
          - os: macos-13
            target: x86_64-apple-darwin
          - os: windows-latest
            target: x86_64-pc-windows-msvc
          - os: ubuntu-latest
            target: x86_64-unknown-linux-gnu

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build backend
        run: pyinstaller cortex-backend.spec --noconfirm

      - name: Rename binary
        run: |
          mv dist/cortex-backend dist/cortex-backend-${{ matrix.target }}

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: backend-${{ matrix.target }}
          path: dist/cortex-backend-${{ matrix.target }}*
```

## Size Optimization

### Strategies

1. **Exclude unused modules**:

```python
# In spec file
excludes=[
    'tkinter',
    'matplotlib',
    'PIL',
    'numpy.testing',
    # Add more as identified
]
```

2. **Use UPX compression**:

```bash
pyinstaller cortex-backend.spec --upx-dir=/path/to/upx
```

3. **Strip debug symbols** (Linux/macOS):

```bash
strip dist/cortex-backend
```

### Expected Sizes

| Platform | Unoptimized | Optimized |
| -------- | ----------- | --------- |
| macOS    | ~150 MB     | ~80 MB    |
| Windows  | ~120 MB     | ~60 MB    |
| Linux    | ~100 MB     | ~50 MB    |

## Risks & Mitigations

### Risk: Cross-Platform Bundling Complexity

**Concern**: Shipping Python with a desktop app is complex.

**Mitigations**:

- Extensive testing on all platforms before each release
- CI/CD builds on actual platform runners (not cross-compilation)
- Fallback: guide users to install Python manually if bundling fails

### Risk: Binary Size

**Concern**: Python bundles are large (50-150 MB).

**Mitigations**:

- UPX compression reduces size by 30-50%
- Exclude unnecessary dependencies
- Consider splitting into main binary + lazy-loaded modules

### Risk: Startup Time

**Concern**: PyInstaller binaries have slow startup.

**Mitigations**:

- Start sidecar early in Tauri initialization
- Show loading indicator while backend initializes
- Use `--onefile` only for distribution, `--onedir` for development

## Debugging Bundled Builds

### Enable Console Output

```python
# In spec file for debugging
exe = EXE(
    ...
    console=True,  # Show console window
)
```

### Check for Missing Imports

```bash
# Run with verbose output
./cortex-backend --verbose

# Or check PyInstaller warnings
pyinstaller cortex-backend.spec --debug=imports
```

### Common Issues

| Issue             | Symptom                          | Solution               |
| ----------------- | -------------------------------- | ---------------------- |
| Missing module    | `ModuleNotFoundError` at runtime | Add to `hiddenimports` |
| Missing data file | `FileNotFoundError`              | Add to `datas` in spec |
| Native extension  | `ImportError: DLL load failed`   | Add to `binaries`      |

## Related Documentation

- [Python Backend Architecture](./architecture.md) - Backend structure
- [Python Sidecar](../architecture/python-sidecar.md) - Why this approach
