# Developer Documentation

Technical documentation for building and extending Cortex. These docs describe established patterns and are intended for both human developers and AI coding agents.

## Product & Vision

| Document                                        | Description                                      |
| ----------------------------------------------- | ------------------------------------------------ |
| [Product Vision](./product/vision.md)           | What Cortex is, why local-first, core principles |
| [Roadmap](./product/roadmap.md)                 | Future features and expansion plans              |
| [Success Metrics](./product/success-metrics.md) | How to measure user and technical success        |

## Architecture & Patterns

| Document                                                   | Description                                             |
| ---------------------------------------------------------- | ------------------------------------------------------- |
| [Architecture Guide](./architecture/architecture-guide.md) | High-level overview, mental models, system architecture |
| [Python Sidecar](./architecture/python-sidecar.md)         | Why Tauri + Python hybrid, IPC patterns                 |
| [Rust Architecture](./architecture/rust-architecture.md)   | Rust module organization and patterns                   |
| [State Management](./architecture/state-management.md)     | Three-layer state onion, Zustand, TanStack Query        |
| [Error Handling](./architecture/error-handling.md)         | Error propagation, user feedback, retry patterns        |

## AI & Machine Learning

| Document                                   | Description                            |
| ------------------------------------------ | -------------------------------------- |
| [AI Overview](./ai/overview.md)            | Provider architecture, model selection |
| [Ollama Integration](./ai/ollama.md)       | Local AI setup, model management       |
| [Cloud Providers](./ai/cloud-providers.md) | OpenAI/Anthropic via LiteLLM           |
| [Embeddings](./ai/embeddings.md)           | Vector embedding strategy, chunking    |
| [LangGraph Workflows](./ai/workflows.md)   | AI processing pipelines                |

## Python Backend

| Document                                                 | Description                                  |
| -------------------------------------------------------- | -------------------------------------------- |
| [Backend Architecture](./python-backend/architecture.md) | FastAPI structure, endpoints, database layer |
| [Bundling](./python-backend/bundling.md)                 | PyInstaller, cross-platform distribution     |

## Core Systems

| Document                                                   | Description                                     |
| ---------------------------------------------------------- | ----------------------------------------------- |
| [Command System](./core-systems/command-system.md)         | Unified action dispatch, command registration   |
| [Keyboard Shortcuts](./core-systems/keyboard-shortcuts.md) | Global shortcut handling, platform modifiers    |
| [Menus](./core-systems/menus.md)                           | Native menu building with i18n                  |
| [Quick Panes](./core-systems/quick-panes.md)               | Multi-window quick entry pattern                |
| [Browser Extension](./core-systems/browser-extension.md)   | Content capture from browser                    |
| [Tauri Commands](./core-systems/tauri-commands.md)         | Type-safe Rust-TypeScript bridge (tauri-specta) |
| [Tauri Plugins](./core-systems/tauri-plugins.md)           | Plugin usage and configuration                  |

## UI & UX

| Document                                         | Description                                 |
| ------------------------------------------------ | ------------------------------------------- |
| [UI Patterns](./ui-ux/ui-patterns.md)            | CSS architecture, shadcn/ui components      |
| [Internationalization](./ui-ux/i18n-patterns.md) | Translation system, RTL support             |
| [Notifications](./ui-ux/notifications.md)        | Toast and native notifications              |
| [Cross-Platform](./ui-ux/cross-platform.md)      | Platform detection, OS-specific adaptations |

## Data & Storage

| Document                                               | Description                                  |
| ------------------------------------------------------ | -------------------------------------------- |
| [Data Persistence](./data-storage/data-persistence.md) | File storage patterns, atomic writes, SQLite |
| [sqlite-vec](./data-storage/sqlite-vec.md)             | Vector storage for semantic search           |
| [External APIs](./data-storage/external-apis.md)       | HTTP API calls, authentication, caching      |

## Quality & Tooling

| Document                                                              | Description                                             |
| --------------------------------------------------------------------- | ------------------------------------------------------- |
| [Static Analysis](./quality-tooling/static-analysis.md)               | ESLint, Prettier, ast-grep, knip, jscpd, React Compiler |
| [Writing ast-grep Rules](./quality-tooling/writing-ast-grep-rules.md) | AI reference for creating custom rules                  |
| [Testing](./quality-tooling/testing.md)                               | Test patterns, Tauri mocking                            |
| [Bundle Optimization](./quality-tooling/bundle-optimization.md)       | Bundle size management                                  |
| [Logging](./quality-tooling/logging.md)                               | Rust and TypeScript logging                             |
| [Writing Docs](./quality-tooling/writing-docs.md)                     | Guide for creating and maintaining these docs           |

## Release & Distribution

| Document                          | Description                            |
| --------------------------------- | -------------------------------------- |
| [Releases](./release/releases.md) | Release process, signing, auto-updates |

---

**Updating these docs:** When adding new patterns or systems, update the relevant doc file and add a link here if creating a new document.
