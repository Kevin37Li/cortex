# Architecture Guide

High-level architectural overview and mental models for Cortex.

## What is Cortex?

Cortex is a **local-first, AI-powered personal knowledge management system**. It acts as an external brain for knowledge workers—capturing content from anywhere, using AI to understand it deeply, connecting related ideas automatically, and surfacing relevant knowledge when you need it.

### Core Loop

```
Capture → Process → Search → Chat
```

1. **Capture**: Zero-friction content ingestion (browser extension, files, quick notes)
2. **Process**: AI-powered content analysis, chunking, and embedding
3. **Search**: Hybrid semantic + keyword search across your knowledge base
4. **Chat**: Ask questions with AI-generated answers grounded in your content

### Core Principles

- **Local-First**: All data stays on your device in a single SQLite file
- **Privacy by Default**: No accounts, no cloud sync, no telemetry
- **Optional Cloud AI**: Choose Ollama (local) or cloud providers (OpenAI/Anthropic)
- **Keyboard-First**: Power users live on the keyboard with global shortcuts
- **Information Density**: Show more, scroll less—built for productivity
- **AI as Enhancement**: AI finds and connects; you control the narrative

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                 Tauri Desktop Application (Rust)                      │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │              React Frontend (TypeScript)                         │ │
│  │  • UI rendering & interactions                                   │ │
│  │  • State management (Zustand + TanStack Query)                  │ │
│  │  • Command palette, keyboard shortcuts, menus                    │ │
│  └────────────────────────┬────────────────────────────────────────┘ │
│                           │ Tauri IPC (type-safe via tauri-specta)   │
│  ┌────────────────────────▼────────────────────────────────────────┐ │
│  │                    Rust Backend                                  │ │
│  │  • Window management & system tray                               │ │
│  │  • File system access (security validation)                      │ │
│  │  • Process management (Python sidecar lifecycle)                 │ │
│  └────────────────────────┬────────────────────────────────────────┘ │
└───────────────────────────┼──────────────────────────────────────────┘
                            │ localhost:8742 (HTTP + WebSocket)
┌───────────────────────────▼──────────────────────────────────────────┐
│                Python Sidecar Backend (FastAPI)                       │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │            LangGraph Workflows                                   │ │
│  │  • Content processing    • Adaptive search                       │ │
│  │  • RAG chat              • Connection discovery                  │ │
│  │  • Daily digest                                                  │ │
│  └────────────────────────┬────────────────────────────────────────┘ │
│                           │                                          │
│  ┌────────────────────────▼────────────────────────────────────────┐ │
│  │          AI Provider Abstraction (LiteLLM)                       │ │
│  │  • Ollama (local)       • OpenAI, Anthropic (cloud)              │ │
│  └────────────────────────┬────────────────────────────────────────┘ │
│                           │                                          │
│  ┌────────────────────────▼────────────────────────────────────────┐ │
│  │          Database Layer (SQLite + sqlite-vec)                    │ │
│  │  • Relational data      • Vector embeddings                      │ │
│  │  • Full-text search     • Repository pattern                     │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Why Tauri + Python?

| Layer         | Technology          | Rationale                                                |
| ------------- | ------------------- | -------------------------------------------------------- |
| Desktop Shell | Tauri (Rust)        | Native performance, ~10MB footprint, security-first      |
| Frontend      | React + TypeScript  | Rich ecosystem, reactive UI, type safety                 |
| AI Backend    | Python (FastAPI)    | Mature AI ecosystem (LangGraph, LangChain, transformers) |
| Database      | SQLite + sqlite-vec | Single-file, portable, embedded vector search            |

The hybrid architecture adds complexity but is essential: Rust handles security-critical operations and native integration, while Python provides access to the AI ecosystem.

## Mental Models

### 1. State Ownership

State is owned by different systems based on its nature—URL state in TanStack Router, component state in useState, global UI state in Zustand, and server data in TanStack Query.

**Decision Tree:**

```
Is this state derived from the URL?
├─ Yes → TanStack Router (route params)
└─ No → Is this data needed across multiple components?
    ├─ No → useState
    └─ Yes → Does this data persist between sessions?
        ├─ No → Zustand
        └─ Yes → TanStack Query
```

See [state-management.md](./state-management.md) for the full ownership table and implementation details.

### 2. Command-Centric Design

All user actions flow through a centralized [command system](../core-systems/command-system.md):

```
Menu Click ─────────┐
Keyboard Shortcut ──┼──▶ Command System ──▶ State Update
Command Palette ────┘
```

- **Commands** are pure objects with `execute()` functions
- **Context** provides all state and actions commands need
- **Registration** merges commands from different domains at runtime

This decouples UI triggers from implementations, enabling consistent behavior across all interaction methods.

### 3. Event-Driven Bridge

Rust and React communicate through events for loose coupling:

```
Rust Event → emit() → React listen() → Handler → State Update
```

This ensures native operations (menu clicks, system tray) trigger the same logic as keyboard shortcuts.

### 4. LangGraph Workflow Pipelines

AI operations use LangGraph for orchestrated, resumable workflows:

```
Input → Node₁ → Conditional Edge → Node₂ → ... → Output
              ↳ Loop back with modified state
```

Key patterns:

- **Typed state** flows through the graph
- **Conditional edges** enable branching and loops
- **Human-in-the-loop** checkpoints for user confirmation
- **Streaming** for real-time progress updates

See [workflows.md](../ai/workflows.md) for implementation details.

## Core Subsystems

### Content Processing Pipeline

When content is captured:

```
Classify → Parse → Chunk → Embed → Extract → Validate → Store → Connect
    │                                   │                           │
    └── Type-specific parsing           └── Retry if quality low    └── Async discovery
```

- **Semantic chunking**: 200-500 tokens respecting document structure
- **Validation loop**: LLM checks extraction quality, retries if poor
- **Connection discovery**: Background task finds related items

### Hybrid Search

Combines vector similarity with keyword matching:

```
Query → Analyze → Vector Search ─┬─▶ Fuse (RRF) → Rank → Results
                  Full-text Search ─┘
```

- **Vector search**: Finds conceptually similar content
- **Full-text search**: Finds exact phrase matches
- **Reciprocal Rank Fusion**: Combines rankings from both approaches

### RAG Chat

Retrieval-Augmented Generation with grounding:

```
Message → Retrieve → Grade Docs → Generate → Ground Check → Response
              │           │              │           │
              └── Rewrite └── Filter     └── Cite    └── Regenerate if needed
```

- **Document grading**: LLM filters irrelevant chunks
- **Query rewriting**: Transforms natural language for better retrieval
- **Grounding check**: Verifies answer is supported by sources

## Data Flow

### Frontend → Python Backend

**HTTP** for CRUD operations:

```typescript
const response = await fetch('http://localhost:8742/api/items', {
  method: 'POST',
  body: JSON.stringify({ title, content, url }),
})
```

**WebSocket** for streaming (chat, processing progress):

```typescript
const ws = new WebSocket(`ws://localhost:8742/api/ws/chat/${id}`)
ws.onmessage = ({ data }) => appendChunk(JSON.parse(data).content)
```

### Frontend → Rust (Tauri)

Type-safe commands via [tauri-specta](https://github.com/specta-rs/tauri-specta):

```typescript
import { commands } from '@/lib/tauri-bindings'

const result = await commands.loadPreferences()
if (result.status === 'ok') {
  console.log(result.data.theme)
}
```

See [tauri-commands.md](../core-systems/tauri-commands.md) for adding new commands.

### Process Lifecycle

```
App Launch → Rust spawns Python → Poll /api/health → Ready
App Close  → SIGTERM → Graceful shutdown (max 5s) → SIGKILL if needed
Crash      → Auto-restart (max 3 attempts) → Error dialog
```

SQLite handles crashes gracefully—user data is safe.

## Component Architecture

```
MainWindow (Top-level orchestrator)
├── TitleBar (Window controls + toolbar)
├── LeftSidebar (Navigation, collections)
├── MainContent (Primary content area)
├── RightSidebar (Context, related items)
└── Global Overlays
    ├── PreferencesDialog (Cmd+,)
    ├── CommandPalette (Cmd+K)
    └── Toaster (Notifications)
```

## File Organization

```
src/                          # React frontend
├── components/
│   ├── layout/              # MainWindowShell, sidebars
│   ├── command-palette/     # Command palette system
│   └── ui/                  # shadcn/ui components
├── hooks/                   # Custom React hooks
├── lib/
│   ├── commands/            # Command system
│   ├── router.ts            # TanStack Router configuration
│   └── tauri-bindings/      # Generated type-safe commands
├── routes/                  # File-based route components
├── services/                # TanStack Query + API calls
└── store/                   # Zustand stores

src-tauri/src/               # Rust backend
├── lib.rs                   # Tauri commands
└── bindings.rs              # Command registration

python-backend/src/          # Python sidecar
├── api/                     # FastAPI routes
├── workflows/               # LangGraph workflows
├── providers/               # AI provider implementations
├── db/                      # Database layer
└── services/                # Business logic
```

## Security Architecture

### Defense in Depth

| Layer              | Protection                                  |
| ------------------ | ------------------------------------------- |
| Tauri Capabilities | Window-specific permissions                 |
| Rust Validation    | All file paths validated before access      |
| CSP                | No external scripts, strict content policy  |
| Atomic Writes      | Write to temp, rename (prevents corruption) |
| Keychain           | API keys in OS keychain, never in IPC       |

### Blocked Paths (Rust)

```rust
fn is_blocked_directory(path: &Path) -> bool {
    let blocked = ["/System/", "/usr/", "/etc/", "/.ssh/"];
    blocked.iter().any(|p| path.starts_with(p))
}
```

### Input Sanitization

```rust
pub fn sanitize_filename(filename: &str) -> String {
    filename.chars()
        .filter(|c| !['/', '\\', ':', '*', '?', '"', '<', '>', '|'].contains(c))
        .collect()
}
```

See [Tauri Security Documentation](https://v2.tauri.app/security/) for detailed guidance.

## Pattern Dependencies

Understanding how patterns work together:

```
Command System
├── Depends on: State Management (context)
├── Integrates with: Keyboard Shortcuts, Menus
└── Enables: Consistent behavior across UI

State Management
├── Enables: Performance (getState pattern)
├── Supports: Data Persistence, UI State
└── Foundation for: All other systems

LangGraph Workflows
├── Depends on: AI Providers, Database
├── Enables: Complex multi-step AI operations
└── Foundation for: Processing, Search, Chat

Event-Driven Bridge
├── Enables: Rust-React communication
├── Supports: Security (validation in Rust)
└── Foundation for: Menus, System Tray
```

## Core Systems Documentation

| System             | Documentation                                                               |
| ------------------ | --------------------------------------------------------------------------- |
| AI Overview        | [ai/overview.md](../ai/overview.md)                                         |
| AI Workflows       | [ai/workflows.md](../ai/workflows.md)                                       |
| Python Backend     | [python-backend/architecture.md](../python-backend/architecture.md)         |
| Command System     | [core-systems/command-system.md](../core-systems/command-system.md)         |
| Keyboard Shortcuts | [core-systems/keyboard-shortcuts.md](../core-systems/keyboard-shortcuts.md) |
| Tauri Commands     | [core-systems/tauri-commands.md](../core-systems/tauri-commands.md)         |
| Data Persistence   | [data-storage/data-persistence.md](../data-storage/data-persistence.md)     |
| State Management   | [state-management.md](./state-management.md)                                |

## Anti-Patterns to Avoid

| Anti-Pattern                    | Why It's Bad             | Do This Instead             |
| ------------------------------- | ------------------------ | --------------------------- |
| State in wrong layer            | Confuses ownership       | Follow the onion model      |
| Direct Rust-React coupling      | Tight coupling           | Use command system + events |
| Store subscription in callbacks | Render cascades          | Use `getState()` pattern    |
| Skipping input validation       | Security vulnerabilities | Always validate in Rust     |
| Synchronous AI calls            | Blocks UI                | Use workflows + streaming   |
| Magic/implicit patterns         | Hard to follow           | Prefer explicit, clear code |

## Adding New Features

1. **Commands** - Add to appropriate command group file
2. **State** - Choose appropriate layer (useState/Zustand/TanStack Query)
3. **AI Operations** - Create LangGraph workflow in Python backend
4. **UI** - Follow component architecture
5. **Persistence** - Use established [data-persistence.md](../data-storage/data-persistence.md) patterns
6. **Testing** - Add tests following [testing.md](../quality-tooling/testing.md) patterns
7. **Documentation** - Update relevant docs
