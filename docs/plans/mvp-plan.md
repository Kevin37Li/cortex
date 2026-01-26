# Cortex MVP Implementation Plan

**Status:** Phase 1 Complete - In Progress
**Version:** 1.2
**Date:** January 2026
**Last Reviewed:** Phase 1 audit completed 2026-01-26; architecture patterns validated against `docs/developer/`

---

## Executive Summary

Cortex is a **local-first, AI-powered personal knowledge management system** that captures content from multiple sources, uses AI to understand and connect it, and surfaces knowledge through natural conversation and semantic search—all while keeping user data completely private on their device.

**The MVP delivers the core capture → process → search → chat loop:**

1. Users save content from their browser or desktop
2. AI processes content to extract meaning and generate embeddings
3. Users search their knowledge using natural language (semantic + keyword)
4. Users chat with their knowledge base using RAG, with citations back to sources

**Target outcome:** A functional desktop application with Chrome extension that demonstrates the core value proposition of AI-powered knowledge retrieval from user-owned data.

---

## Scope Definition

### In Scope (MVP)

| Category          | Included                                                              |
| ----------------- | --------------------------------------------------------------------- |
| **Capture**       | Browser extension (Chrome), quick notes (desktop), manual file import |
| **Content Types** | Web pages (HTML), plain text notes, Markdown files                    |
| **AI Processing** | Content summarization, entity extraction, embedding generation        |
| **Search**        | Semantic search (vector), keyword search (FTS), hybrid ranking        |
| **Chat**          | RAG-based conversation with citations, streaming responses            |
| **Connections**   | Automatic similarity-based connections between items                  |
| **AI Providers**  | Ollama (local), OpenAI (cloud option)                                 |
| **Settings**      | AI provider config, theme (light/dark), basic preferences             |

### Out of Scope (Deferred)

| Category              | Deferred To                                               |
| --------------------- | --------------------------------------------------------- | --------- |
| **Content Types**     | PDF parsing, audio/video transcription                    | Phase 2   |
| **Browser Support**   | Firefox, Safari extensions                                | Phase 2   |
| **Mobile**            | Mobile companion app                                      | Phase 3   |
| **Advanced Features** | Writing assistant, smart collections, graph visualization | Phase 2-3 |
| **Collaboration**     | Team features, peer-to-peer sync                          | Phase 3   |
| **Ecosystem**         | Plugin API, Obsidian/Notion sync                          | Phase 3   |
| **Daily Digest**      | Proactive knowledge surfacing                             | Phase 2   |

### Explicit Non-Goals

- Not a note-taking app (Obsidian/Notion are better for that)
- Not a bookmark manager (simpler tools exist)
- Not a cloud service or sync platform
- Not a general AI assistant (only knows what the user saved)

---

## Core Features

### Priority 1: Foundational

#### 1.1 Desktop Application Shell

The main Tauri application with three-pane layout (sidebar, content, detail panel), window management, and theme support.

**Includes:**

- Main window with responsive layout
- Left sidebar: navigation (All Items, Conversations), quick note creation
- Command palette (Cmd+K) for discoverability
- Preferences dialog
- Light/dark/system theme

**Excludes:**

- Custom keyboard shortcut configuration
- Multiple windows
- Tray/menu bar mode

#### 1.2 Python Backend Server

FastAPI server running locally that handles all AI processing and data storage.

**Includes:**

- REST endpoints for items, search, settings
- WebSocket for streaming chat
- Background processing queue
- SQLite database with sqlite-vec for vector storage
- Health check endpoints

**Excludes:**

- Remote access (localhost only)
- Authentication (single-user, local-only)

### Priority 2: Core Loop

#### 2.1 Content Capture

Three capture methods: browser extension, desktop quick notes, and file import.

**Browser Extension (Chrome) includes:**

- Save full page content
- Save selected text with source URL
- Offline queue when desktop app unavailable
- Status indicator (connected/offline)
- Basic keyboard shortcut (Cmd+Shift+S)

**Browser Extension excludes:**

- Page annotation
- Highlighting
- Tag/folder assignment at capture time

**Desktop Quick Notes includes:**

- Simple text input
- Markdown support in content
- Immediate save to backend

**File Import includes:**

- Manual file selection dialog
- Text and Markdown files only

**File Import excludes:**

- Drag-and-drop
- Watch folders
- Batch import UI

#### 2.2 Content Processing Pipeline

LangGraph workflow that transforms raw content into searchable, connected knowledge.

**Includes:**

- Content type classification (HTML vs text)
- HTML parsing using Readability
- Semantic chunking (200-500 tokens)
- Embedding generation (nomic-embed-text or OpenAI)
- Metadata extraction: summary, key concepts, named entities
- Validation step with retry on failure
- Processing status indicators in UI

**Excludes:**

- PDF parsing
- Audio/video transcription
- Image OCR
- Custom extraction rules

#### 2.3 Search System

Hybrid search combining semantic understanding with exact phrase matching.

**Includes:**

- Vector search (semantic similarity)
- Full-text search (exact keywords/phrases)
- Reciprocal Rank Fusion for combining results
- Search results with relevance indicators
- Click-through to full item view

**Excludes:**

- Query decomposition for complex queries
- Automatic query expansion
- Faceted filtering (by date, source, etc.)
- Saved searches

#### 2.4 Chat Interface

RAG-based conversation with the knowledge base.

**Includes:**

- Natural language questions
- Document retrieval and relevance grading
- LLM response with citations to sources
- Streaming responses
- Conversation history (stored locally)
- Multiple conversations

**Excludes:**

- Query rewriting/reformulation
- Grounding check (hallucination detection)
- Chat within item context
- Export conversations

### Priority 3: Intelligence Features

#### 3.1 Connection Discovery

Automatic relationship detection between items.

**Includes:**

- Similarity-based connections (embedding distance)
- Display connections in item detail view
- Bidirectional relationships

**Excludes:**

- Entity-based connections
- Temporal clustering
- Connection strength scoring
- Manual connection management
- Graph visualization

#### 3.2 AI Provider Configuration

Setup and management of local vs cloud AI.

**Includes:**

- First-run setup wizard
- Ollama status detection
- Model selection (embedding model, chat model)
- OpenAI API key configuration (stored in OS keychain)
- Provider switching

**Excludes:**

- Anthropic Claude integration (simpler to start with OpenAI only)
- Model download management within app
- Per-task provider routing
- Cost tracking

---

## Technical Approach

### Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│              Tauri Desktop App                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  React 19 + Tailwind v4 + shadcn/ui             │  │
│  │  State: Zustand (UI) + TanStack Query (data)    │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Rust Backend (Tauri)                            │  │
│  │  - Window management, file system, process mgmt │  │
│  └──────────────────┬───────────────────────────────┘  │
└─────────────────────┼──────────────────────────────────┘
                      │ localhost:8742
┌─────────────────────▼──────────────────────────────────┐
│              Python Backend                            │
│  FastAPI + LangGraph + SQLite + sqlite-vec            │
└────────────────────────────────────────────────────────┘
```

### Key Technical Decisions

| Decision              | Choice                     | Rationale                                                     |
| --------------------- | -------------------------- | ------------------------------------------------------------- |
| **Desktop Framework** | Tauri v2 (Rust)            | Small binary (~10MB), native performance, secure              |
| **Frontend**          | React 19 + Tailwind v4     | Modern, performant, React Compiler for auto-optimization      |
| **AI Processing**     | Python + FastAPI           | Mature AI ecosystem (LangGraph, LangChain), rapid development |
| **Database**          | SQLite + sqlite-vec        | Single-file local storage, vector search built-in             |
| **Local AI**          | Ollama                     | Easy setup, good model selection, active community            |
| **Cloud AI**          | LiteLLM                    | Unified interface for OpenAI (MVP) and future providers       |
| **IPC**               | localhost HTTP + WebSocket | Standard, debuggable, Python-native                           |

### Performance Targets

| Metric                      | Target                   |
| --------------------------- | ------------------------ |
| App startup to usable       | < 3 seconds              |
| Search keystroke to results | < 100ms (debounced)      |
| Full search execution       | < 500ms for 10K items    |
| Chat first token (local)    | < 2 seconds              |
| Chat first token (cloud)    | < 1 second               |
| Item processing             | < 30 seconds per webpage |

### Security Approach

- **No accounts required** - single-user local application
- **Data never leaves device** - except optional cloud AI inference
- **API keys in OS keychain** - never stored on disk
- **Rust handles all file operations** - with path validation
- **localhost-only backend** - not accessible from network

---

## Development Standards

These standards apply to **all phases** and ensure consistency with documented architecture patterns.

### Cross-Cutting Requirements

| Requirement              | Reference                                       | Action                                                                      |
| ------------------------ | ----------------------------------------------- | --------------------------------------------------------------------------- |
| **i18n**                 | `docs/developer/ui-ux/i18n-patterns.md`         | All user-facing strings must use translation keys in `/locales/*.json`      |
| **RTL Support**          | `docs/developer/ui-ux/i18n-patterns.md`         | Use CSS logical properties (`text-start` not `text-left`)                   |
| **Command Registration** | `docs/developer/core-systems/command-system.md` | Register new keyboard shortcuts in `src/lib/commands/` with `labelKey`      |
| **Tauri Bindings**       | `docs/developer/core-systems/tauri-commands.md` | Run `bun run rust:bindings` after any Rust command changes                  |
| **Error Handling**       | `docs/developer/architecture/error-handling.md` | Follow patterns for Rust Result types, Python exceptions, TypeScript errors |
| **Testing**              | `docs/developer/quality-tooling/testing.md`     | Write tests for business logic; mock Tauri commands per testing patterns    |

### State Management Decision Tree

Per `docs/developer/architecture/state-management.md`, choose the appropriate layer:

```
useState (component-local) → Zustand (global UI) → TanStack Query (persistent data)
```

| Feature              | State Layer    | Rationale                                |
| -------------------- | -------------- | ---------------------------------------- |
| Item list data       | TanStack Query | Persistent data from Python backend      |
| Search UI visibility | Zustand        | Global UI state shared across components |
| Chat messages        | TanStack Query | Persistent with WebSocket updates        |
| Sidebar visibility   | Zustand        | Already documented pattern               |
| Form input values    | useState       | Component-local, not shared              |

### Anti-Patterns to Avoid

| Anti-Pattern                     | Why Bad                                            | Correct Pattern                                   |
| -------------------------------- | -------------------------------------------------- | ------------------------------------------------- |
| `const { value } = useUIStore()` | Subscribes to entire store, causes render cascades | `useUIStore(state => state.value)`                |
| Manual `useMemo`/`useCallback`   | React Compiler handles this automatically          | Let compiler optimize                             |
| `await invoke('command')`        | No type safety                                     | `import { commands } from '@/lib/tauri-bindings'` |
| Synchronous AI calls             | Blocks UI                                          | Use async patterns with progress indicators       |

### Additional Cross-Cutting Notes

- **New Zustand stores**: When adding new stores, update `.ast-grep/rules/zustand/no-destructure.yml` per `state-management.md`
- **TanStack Query service hooks**: All Python backend API calls must be wrapped in TanStack Query hooks (in `src/services/`), not called directly with `fetch()` in components
- **Cloud AI abstraction**: Use LiteLLM as the unified interface for cloud providers (OpenAI at MVP, designed for Anthropic later) per `cloud-providers.md`
- **Embedding model consistency**: Never mix embeddings from different models in the same database per `embeddings.md`. Track active model in metadata

### Quality Gate (Per Phase)

Before marking any phase complete:

1. Run `bun run check:all` and resolve all issues
2. Verify all new UI strings have translation keys
3. Confirm tests pass for new functionality
4. Review code for anti-patterns listed above

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2) ✅ COMPLETE

**Goal:** Working desktop shell communicating with Python backend

**Backend Tasks:**

- [x] FastAPI project structure with proper layering
- [x] SQLite schema with sqlite-vec extension
- [x] Database repository pattern implementation
- [x] CRUD endpoints for items (`/api/items`)
- [x] Health check endpoint (`/api/health`)
- [x] Ollama provider integration and health check
- [x] Set up pytest infrastructure with fixtures for file-based SQLite using `tmp_path` (sqlite-vec requires file-based databases)
- [x] Write tests for repository patterns and CRUD endpoints (92% coverage)

**Frontend Tasks:**

- [x] Tauri project with React 19 + Tailwind v4
- [x] Main window three-pane layout (state: Zustand for sidebar visibility)
- [x] Theme system (light/dark/system)
- [x] Command palette (Cmd+K) shell - registered in `src/lib/commands/`
- [x] Preferences dialog skeleton (General, Appearance, Advanced panes)
- [x] Window state persistence (via `tauri-plugin-window-state`)
- [x] Basic routing and navigation (TanStack Router with hash-based routing)
- [x] Add translation keys for all UI strings in `/locales/en.json` (139 keys, English + Chinese)
- [x] Run `bun run rust:bindings` after adding Rust commands (6 commands generated)

**Quality Gate:**

- [x] `bun run check:all` passes
- [x] All UI strings use translation keys
- [x] Python tests pass

**Remaining items deferred from Phase 1 to Phase 2:**

- [ ] Python sidecar lifecycle management in Rust (spawn, health poll, restart, shutdown) per `docs/developer/architecture/python-sidecar.md`

**Milestone:** ✅ Can launch app, see empty item list, backend responds to health checks

### Phase 2: Content Pipeline (Weeks 2-3)

**Goal:** Save content and process it with AI

**Backend Tasks:**

- [ ] Python sidecar lifecycle management in Rust (spawn, health poll, restart, shutdown) per `python-sidecar.md`
- [ ] Create `workflows/processing.py` implementing the LangGraph content processing graph
- [ ] Content parsing (HTML via Readability, plain text)
- [ ] Semantic chunking with RecursiveCharacterTextSplitter
- [ ] Embedding generation (Ollama + OpenAI providers)
- [ ] Embedding dimension consistency enforcement — track model in chunk metadata, prevent mixing (768 vs 1536 dims)
- [ ] Metadata extraction (summary, entities, concepts)
- [ ] Implement `ProcessingQueue` in `services/processing.py` for background processing with status updates
- [ ] Implement embedding management in `services/embeddings.py`
- [ ] Processing status events (WebSocket)
- [ ] Add `ProcessingError` to `exceptions.py` and register its FastAPI exception handler in `main.py`
- [ ] Add processing queue endpoints: `GET /api/processing/queue`, `POST /api/processing/retry`
- [ ] Write tests for processing workflow steps

**Frontend Tasks:**

- [ ] Create TanStack Query service hooks in `src/services/items.ts` wrapping API calls
- [ ] Quick note creation UI (state: useState for form, TanStack Query for submission)
- [ ] File import dialog
- [ ] Item list with processing status indicators (state: TanStack Query)
- [ ] Item detail view (content, metadata, status)
- [ ] Progress indicators for async AI operations
- [ ] Add translation keys for processing status messages

**Quality Gate:**

- [ ] `bun run check:all` passes
- [ ] All UI strings use translation keys
- [ ] Python tests pass for workflow steps

**Milestone:** Can create a note → see it process → view extracted metadata

### Phase 3: Search (Week 3)

**Goal:** Find content using natural language

**Backend Tasks:**

- [ ] Create `workflows/search.py` implementing the LangGraph search graph
- [ ] Vector search implementation (sqlite-vec)
- [ ] Full-text search (FTS5)
- [ ] Hybrid search with Reciprocal Rank Fusion
- [ ] Create `api/search.py` route file and register router in `main.py`
- [ ] Search endpoint (`POST /api/search`)
- [ ] Write tests for search ranking and fusion

**Frontend Tasks:**

- [ ] Create TanStack Query service hooks in `src/services/search.ts`
- [ ] Search input with keyboard shortcut (Cmd+F) - register per `command-system.md`
- [ ] Search results display with relevance scores (state: TanStack Query)
- [ ] Click-through to item detail
- [ ] Empty state and loading states
- [ ] Add translation keys for search UI strings

**Quality Gate:**

- [ ] `bun run check:all` passes
- [ ] Search command registered with `labelKey` translation
- [ ] Python tests pass for search functionality

**Milestone:** Can search items and find relevant results

### Phase 4: Chat (Week 4)

**Goal:** Have conversations with your knowledge

**Backend Tasks:**

- [ ] Conversation and message data models (schema additions for `conversations` and `messages` tables)
- [ ] Create `ConversationRepository` and `MessageRepository` in `db/repositories/`
- [ ] Create `workflows/chat.py` implementing the LangGraph RAG graph (retrieve → grade → generate)
- [ ] Citation extraction and formatting
- [ ] Create `api/chat.py` route file and register router in `main.py`
- [ ] WebSocket streaming endpoint with error handling per `error-handling.md`
- [ ] Conversation persistence
- [ ] Implement FastAPI exception handlers for streaming errors
- [ ] Write tests for RAG workflow and citation extraction

**Frontend Tasks:**

- [ ] Create TanStack Query service hooks in `src/services/chat.ts`
- [ ] Chat panel UI (state: TanStack Query for messages with WebSocket updates)
- [ ] Message input and streaming display
- [ ] Citation links to source items
- [ ] Conversation list and switching
- [ ] New conversation creation
- [ ] Add translation keys for chat UI strings

**Quality Gate:**

- [ ] `bun run check:all` passes
- [ ] All chat UI strings use translation keys
- [ ] Python tests pass for RAG workflow

**Milestone:** Can ask questions and get cited answers from knowledge base

### Phase 5: Browser Extension (Week 5)

**Goal:** Capture content from the web

**Extension Tasks:**

- [ ] Plasmo project setup for Chrome
- [ ] Content extraction (full page and selection)
- [ ] Desktop app communication (localhost:8742)
- [ ] Offline queue with retry logic
- [ ] Status indicator (connected/offline)
- [ ] Keyboard shortcut (Cmd+Shift+S)
- [ ] Popup UI for save confirmation
- [ ] Add translation keys for extension UI strings (if i18n supported)

**Integration Tasks:**

- [ ] Backend endpoint for extension submissions
- [ ] Queue processing for extension items
- [ ] Source URL tracking and display
- [ ] Write integration tests for extension → backend flow

**Quality Gate:**

- [ ] `bun run check:all` passes
- [ ] Extension builds without errors
- [ ] Integration tests pass

**Milestone:** Can save articles from Chrome → see them in desktop app

### Phase 6: Polish & Integration (Week 6)

**Goal:** Production-ready MVP

**Feature Tasks:**

- [ ] Create `workflows/connections.py` implementing similarity-based connection discovery
- [ ] Connection discovery (similarity-based)
- [ ] Connections display in item detail
- [ ] Implement `CloudProvider` in `providers/cloud.py` using LiteLLM per `cloud-providers.md` (designed to support multiple providers, MVP configures OpenAI only)
- [ ] Create `api/settings.py` route file and register router in `main.py`
- [ ] AI provider setup wizard (first-run)
- [ ] Ollama status and model selection UI
- [ ] OpenAI API key configuration
- [ ] Add translation keys for setup wizard and settings UI

**Quality Tasks:**

- [ ] Error handling review: verify all layers follow `error-handling.md`
- [ ] User-friendly error messages for all error states
- [ ] End-to-end testing of core flows

**Performance Tasks (verify against Performance Targets):**

- [ ] App startup < 3 seconds
- [ ] Search keystroke to results < 100ms (debounced)
- [ ] Full search execution < 500ms for 10K items
- [ ] Chat first token (local) < 2 seconds
- [ ] Chat first token (cloud) < 1 second
- [ ] Item processing < 30 seconds per webpage
- [ ] Memory usage < 500MB at idle
- [ ] Profile and optimize any metrics not meeting targets

**Documentation Tasks:**

- [ ] Update relevant `docs/developer/` files for new patterns discovered
- [ ] Verify all architecture decisions are documented

**Final Quality Gate:**

- [ ] `bun run check:all` passes with no warnings
- [ ] All UI strings use translation keys
- [ ] All Python tests pass
- [ ] All frontend tests pass
- [ ] Performance targets met

**Milestone:** Complete MVP ready for user testing

---

## Dependencies & Risks

### External Dependencies

| Dependency                | Risk Level | Mitigation                                                        |
| ------------------------- | ---------- | ----------------------------------------------------------------- |
| **Ollama**                | Medium     | Required for local AI; fallback to cloud-only mode if unavailable |
| **sqlite-vec**            | Low        | Mature extension; no known issues                                 |
| **Tauri v2**              | Low        | Stable release; active community                                  |
| **LangGraph**             | Low        | Well-documented; used by many projects                            |
| **Chrome Extension APIs** | Low        | Stable Manifest V3; Plasmo abstracts complexity                   |

### Technical Risks

| Risk                                 | Likelihood | Impact | Mitigation                                              |
| ------------------------------------ | ---------- | ------ | ------------------------------------------------------- |
| **Embedding model quality varies**   | Medium     | High   | Test multiple models early; document model requirements |
| **Processing pipeline performance**  | Medium     | Medium | Implement progress indicators; optimize chunking        |
| **Local AI resource usage**          | Medium     | Medium | Recommend minimum specs; implement graceful degradation |
| **Cross-platform compatibility**     | Low        | High   | Test on macOS, Windows, Linux throughout development    |
| **Browser extension store approval** | Low        | Medium | Follow Chrome Web Store guidelines strictly             |

### Ambiguities Requiring Clarification

1. **Minimum system requirements** - What are acceptable minimum specs for local AI? Need to define RAM, CPU, GPU requirements.

2. **Offline behavior** - Should the app work fully offline, or is internet required for cloud AI fallback?

3. **Model download experience** - Should the app manage Ollama model downloads, or require user to do this separately?

4. **Extension publish strategy** - Private use only initially, or publish to Chrome Web Store?

5. **Error recovery for processing failures** - How many retries? Manual retry option? Delete failed items?

---

## Success Criteria

### MVP Complete When:

**Functional Requirements:**

- [ ] User can save content from Chrome via browser extension
- [ ] User can create quick notes in desktop app
- [ ] Content is processed with AI (summary, entities extracted)
- [ ] User can search and find relevant items
- [ ] User can chat with knowledge base and get cited answers
- [ ] Items show automatic connections to related items
- [ ] User can configure local (Ollama) or cloud (OpenAI) AI

**Performance Requirements:**

- [ ] App starts in under 3 seconds
- [ ] Search returns results in under 500ms
- [ ] 95%+ of items process successfully
- [ ] Memory usage under 500MB at idle

**Quality Requirements:**

- [ ] No critical bugs in core flows
- [ ] All error states have user-friendly messages
- [ ] Works on macOS (primary), with Windows/Linux tested

### Not Required for MVP:

- PDF support
- Audio/video support
- Multiple browser support
- Mobile app
- Graph visualization
- Plugin system
- Sync or backup features

---

## Appendix: API Endpoints (MVP)

### Items

```
POST   /api/items              Create item
GET    /api/items              List items (paginated)
GET    /api/items/{id}         Get single item with chunks/connections
PUT    /api/items/{id}         Update item
DELETE /api/items/{id}         Delete item
```

### Search

```
POST   /api/search             Execute search query
```

### Processing

```
GET    /api/processing/queue   Get processing queue status
POST   /api/processing/retry   Retry failed processing
```

### Chat

```
POST   /api/conversations                    Create conversation
GET    /api/conversations                    List conversations
GET    /api/conversations/{id}               Get conversation with messages
DELETE /api/conversations/{id}               Delete conversation
POST   /api/conversations/{id}/messages      Send message (returns sync)
WS     /api/ws/chat/{conversation_id}        Stream responses
```

### Settings

```
GET    /api/settings           Get app settings
PUT    /api/settings           Update settings
```

### Health

```
GET    /api/health             Backend health
GET    /api/health/ollama      Ollama status
```
