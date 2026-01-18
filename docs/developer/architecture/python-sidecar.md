# Python Sidecar Architecture

Why Cortex uses a Tauri + Python hybrid architecture.

## The Decision

Cortex uses a hybrid architecture:

- **Tauri (Rust)** for the desktop shell, window management, and system integration
- **Python (FastAPI)** for AI processing, database access, and business logic

These communicate via localhost HTTP.

## Why Not Pure Rust?

Pure Rust would be ideal for performance and simplicity, but:

| Factor                | Pure Rust                              | Python Sidecar                            |
| --------------------- | -------------------------------------- | ----------------------------------------- |
| **AI ecosystem**      | Immature (limited LangChain/LangGraph) | Mature (full LangChain/LangGraph support) |
| **Development speed** | Slower iteration                       | Faster prototyping                        |
| **ML libraries**      | Limited                                | Comprehensive                             |
| **Learning curve**    | Steep                                  | Moderate                                  |

The Python AI ecosystem is years ahead. LangGraph, the core of our workflow system, is Python-first with limited Rust support.

## Why Not Electron + Node.js?

Electron is the "default" for desktop apps, but:

| Factor              | Electron                  | Tauri                  |
| ------------------- | ------------------------- | ---------------------- |
| **Binary size**     | 150MB+ baseline           | 10MB baseline          |
| **Memory usage**    | Higher (bundled Chromium) | Lower (system webview) |
| **Startup time**    | Slower                    | Faster                 |
| **Node.js AI libs** | Okay but not Python-level | N/A                    |

Tauri gives us native performance with a smaller footprint. The Python sidecar adds what we need for AI.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Tauri Application                         │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Rust Core                            │    │
│  │                                                      │    │
│  │  Responsibilities:                                   │    │
│  │  • Window management (main, quick capture, etc.)    │    │
│  │  • System tray and native menus                     │    │
│  │  • File system access (with permissions)            │    │
│  │  • Process management (spawn/kill Python)           │    │
│  │  • IPC bridge to frontend                           │    │
│  │  • Auto-updates                                      │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               React Frontend                         │    │
│  │                                                      │    │
│  │  Responsibilities:                                   │    │
│  │  • UI rendering                                      │    │
│  │  • User interactions                                 │    │
│  │  • State management (Zustand)                       │    │
│  │  • API calls to Python backend                      │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ localhost:8742 (HTTP/WebSocket)
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Python Backend                             │
│                                                              │
│  Responsibilities:                                          │
│  • AI provider abstraction (Ollama, OpenAI)                │
│  • LangGraph workflow execution                             │
│  • SQLite database access                                   │
│  • Background processing queue                              │
│  • Search and retrieval                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Communication Patterns

### Frontend → Python Backend

Direct HTTP calls for most operations:

```typescript
// In React component
const response = await fetch('http://localhost:8742/api/items', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ title, content, url }),
})
```

### Streaming (Chat, Processing Progress)

WebSocket for real-time updates:

```typescript
// Chat streaming
const ws = new WebSocket(`ws://localhost:8742/api/ws/chat/${conversationId}`)

ws.onmessage = event => {
  const data = JSON.parse(event.data)
  if (data.type === 'chunk') {
    appendToResponse(data.content)
  }
}

ws.send(JSON.stringify({ message: userQuery }))
```

### Rust → Python (Rare)

For operations that must go through Rust (e.g., file access):

```rust
// Rust reads file, sends content to Python
let content = std::fs::read_to_string(path)?;
let client = reqwest::Client::new();
client.post("http://localhost:8742/api/items")
    .json(&CreateItemRequest { content, title, url })
    .send()
    .await?;
```

## Process Lifecycle

### Startup Sequence

```
1. User launches Cortex.app
2. Tauri main process starts
3. Rust spawns Python sidecar as child process
4. Python starts FastAPI on localhost:8742
5. Rust polls /api/health until ready (max 30s)
6. Frontend renders, makes first API call
7. App is ready for use
```

### Shutdown Sequence

```
1. User closes main window
2. Tauri's on_window_event fires
3. Rust sends SIGTERM to Python process
4. Python gracefully shuts down (closes DB, stops workers)
5. Rust waits for Python exit (max 5s)
6. If timeout, Rust sends SIGKILL
7. Tauri exits
```

### Crash Recovery

If Python crashes:

1. Rust detects process termination
2. Rust attempts restart (max 3 times)
3. If restart fails, show error dialog to user
4. User data is safe (SQLite handles this)

```rust
// Monitor sidecar health
loop {
    tokio::time::sleep(Duration::from_secs(5)).await;

    let health = client.get("http://localhost:8742/api/health")
        .timeout(Duration::from_secs(2))
        .send()
        .await;

    if health.is_err() {
        warn!("Backend health check failed, attempting restart");
        restart_sidecar(&app_handle);
    }
}
```

## Trade-offs Accepted

### Two Runtimes

- **Cost**: Slightly more complexity, two languages to maintain
- **Mitigation**: Clear separation of concerns, each runtime does what it's best at

### Bundled Python

- **Cost**: Larger binary size (~50-150 MB for Python bundle)
- **Mitigation**: UPX compression, exclude unused modules, acceptable for desktop app

### IPC Overhead

- **Cost**: Network round-trip for every backend call
- **Mitigation**: Localhost HTTP is fast (<1ms latency), batch operations where possible

### Startup Delay

- **Cost**: ~1-2 seconds to start Python process
- **Mitigation**: Start early, show loading indicator, UI is responsive while backend initializes

## Alternatives Considered

### Alternative 1: Rust-only with llama.cpp

Use Rust bindings to llama.cpp for local inference.

**Pros**: Single runtime, no Python dependency
**Cons**: No LangGraph, limited AI ecosystem, more complex to implement

**Verdict**: Not viable for our workflow complexity.

### Alternative 2: Node.js Sidecar

Use Node.js instead of Python for the backend.

**Pros**: Same language as frontend, better TypeScript integration
**Cons**: AI libraries are less mature than Python

**Verdict**: Python's AI ecosystem advantage outweighs TypeScript convenience.

### Alternative 3: Python Desktop (No Tauri)

Build entire app in Python with PyQt/Tkinter.

**Pros**: Single runtime
**Cons**: UI limitations, larger binary, less native feel

**Verdict**: Tauri gives better UX and smaller bundles.

### Alternative 4: Cloud Backend

Run AI processing in the cloud, desktop is just a client.

**Pros**: No bundling complexity, lighter desktop app
**Cons**: Defeats local-first purpose, requires internet, ongoing costs

**Verdict**: Fundamentally conflicts with our privacy goals.

## Security Considerations

### Local-Only Communication

Python backend only binds to `127.0.0.1`:

```python
uvicorn.run(app, host="127.0.0.1", port=8742)
```

This ensures:

- No external network access to the backend
- Other apps on same machine could connect (acceptable risk for desktop app)

### No Secrets in IPC

API keys are stored in OS keychain, accessed directly by Python:

- Never sent over IPC
- Never logged
- Never included in crash reports

### Process Isolation

Python runs as a separate process:

- Crash doesn't take down the UI
- Memory isolation from frontend
- Can be restarted independently

## Related Documentation

- [Python Backend Architecture](../python-backend/architecture.md) - FastAPI structure
- [Python Bundling](../python-backend/bundling.md) - Packaging for distribution
- [AI Overview](../ai/overview.md) - AI provider architecture
