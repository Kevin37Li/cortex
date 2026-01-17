# Cortex MVP Implementation Plan

**Status:** Draft - Pending Stakeholder Approval
**Version:** 1.0
**Date:** January 2026

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

| Category | Included |
|----------|----------|
| **Capture** | Browser extension (Chrome), quick notes (desktop), manual file import |
| **Content Types** | Web pages (HTML), plain text notes, Markdown files |
| **AI Processing** | Content summarization, entity extraction, embedding generation |
| **Search** | Semantic search (vector), keyword search (FTS), hybrid ranking |
| **Chat** | RAG-based conversation with citations, streaming responses |
| **Connections** | Automatic similarity-based connections between items |
| **AI Providers** | Ollama (local), OpenAI (cloud option) |
| **Settings** | AI provider config, theme (light/dark), basic preferences |

### Out of Scope (Deferred)

| Category | Deferred To |
|----------|-------------|
| **Content Types** | PDF parsing, audio/video transcription | Phase 2 |
| **Browser Support** | Firefox, Safari extensions | Phase 2 |
| **Mobile** | Mobile companion app | Phase 3 |
| **Advanced Features** | Writing assistant, smart collections, graph visualization | Phase 2-3 |
| **Collaboration** | Team features, peer-to-peer sync | Phase 3 |
| **Ecosystem** | Plugin API, Obsidian/Notion sync | Phase 3 |
| **Daily Digest** | Proactive knowledge surfacing | Phase 2 |

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

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Desktop Framework** | Tauri v2 (Rust) | Small binary (~10MB), native performance, secure |
| **Frontend** | React 19 + Tailwind v4 | Modern, performant, React Compiler for auto-optimization |
| **AI Processing** | Python + FastAPI | Mature AI ecosystem (LangGraph, LangChain), rapid development |
| **Database** | SQLite + sqlite-vec | Single-file local storage, vector search built-in |
| **Local AI** | Ollama | Easy setup, good model selection, active community |
| **IPC** | localhost HTTP + WebSocket | Standard, debuggable, Python-native |

### Performance Targets

| Metric | Target |
|--------|--------|
| App startup to usable | < 3 seconds |
| Search keystroke to results | < 100ms (debounced) |
| Full search execution | < 500ms for 10K items |
| Chat first token (local) | < 2 seconds |
| Chat first token (cloud) | < 1 second |
| Item processing | < 30 seconds per webpage |

### Security Approach

- **No accounts required** - single-user local application
- **Data never leaves device** - except optional cloud AI inference
- **API keys in OS keychain** - never stored on disk
- **Rust handles all file operations** - with path validation
- **localhost-only backend** - not accessible from network

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Working desktop shell communicating with Python backend

**Backend Tasks:**
- [ ] FastAPI project structure with proper layering
- [ ] SQLite schema with sqlite-vec extension
- [ ] Database repository pattern implementation
- [ ] CRUD endpoints for items (`/api/items`)
- [ ] Health check endpoint (`/api/health`)
- [ ] Ollama provider integration and health check

**Frontend Tasks:**
- [ ] Tauri project with React 19 + Tailwind v4
- [ ] Main window three-pane layout
- [ ] Theme system (light/dark/system)
- [ ] Command palette (Cmd+K) shell
- [ ] Preferences dialog skeleton
- [ ] Window state persistence
- [ ] Basic routing and navigation

**Milestone:** Can launch app, see empty item list, backend responds to health checks

### Phase 2: Content Pipeline (Weeks 2-3)

**Goal:** Save content and process it with AI

**Backend Tasks:**
- [ ] LangGraph processing workflow implementation
- [ ] Content parsing (HTML via Readability, plain text)
- [ ] Semantic chunking with RecursiveCharacterTextSplitter
- [ ] Embedding generation (Ollama + OpenAI providers)
- [ ] Metadata extraction (summary, entities, concepts)
- [ ] Background processing queue with status updates
- [ ] Processing status events (WebSocket)

**Frontend Tasks:**
- [ ] Quick note creation UI
- [ ] File import dialog
- [ ] Item list with processing status indicators
- [ ] Item detail view (content, metadata, status)

**Milestone:** Can create a note → see it process → view extracted metadata

### Phase 3: Search (Week 3)

**Goal:** Find content using natural language

**Backend Tasks:**
- [ ] Vector search implementation (sqlite-vec)
- [ ] Full-text search (FTS5)
- [ ] Hybrid search with Reciprocal Rank Fusion
- [ ] Search endpoint (`POST /api/search`)

**Frontend Tasks:**
- [ ] Search input with keyboard shortcut (Cmd+F)
- [ ] Search results display with relevance scores
- [ ] Click-through to item detail
- [ ] Empty state and loading states

**Milestone:** Can search items and find relevant results

### Phase 4: Chat (Week 4)

**Goal:** Have conversations with your knowledge

**Backend Tasks:**
- [ ] Conversation and message data models
- [ ] LangGraph RAG workflow (retrieve → grade → generate)
- [ ] Citation extraction and formatting
- [ ] WebSocket streaming endpoint
- [ ] Conversation persistence

**Frontend Tasks:**
- [ ] Chat panel UI
- [ ] Message input and streaming display
- [ ] Citation links to source items
- [ ] Conversation list and switching
- [ ] New conversation creation

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

**Integration Tasks:**
- [ ] Backend endpoint for extension submissions
- [ ] Queue processing for extension items
- [ ] Source URL tracking and display

**Milestone:** Can save articles from Chrome → see them in desktop app

### Phase 6: Polish & Integration (Week 6)

**Goal:** Production-ready MVP

**Tasks:**
- [ ] Connection discovery (similarity-based)
- [ ] Connections display in item detail
- [ ] AI provider setup wizard (first-run)
- [ ] Ollama status and model selection UI
- [ ] OpenAI API key configuration
- [ ] Error handling and user feedback throughout
- [ ] Performance profiling and optimization
- [ ] Memory usage optimization
- [ ] End-to-end testing of core flows
- [ ] Documentation updates

**Milestone:** Complete MVP ready for user testing

---

## Dependencies & Risks

### External Dependencies

| Dependency | Risk Level | Mitigation |
|------------|------------|------------|
| **Ollama** | Medium | Required for local AI; fallback to cloud-only mode if unavailable |
| **sqlite-vec** | Low | Mature extension; no known issues |
| **Tauri v2** | Low | Stable release; active community |
| **LangGraph** | Low | Well-documented; used by many projects |
| **Chrome Extension APIs** | Low | Stable Manifest V3; Plasmo abstracts complexity |

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Embedding model quality varies** | Medium | High | Test multiple models early; document model requirements |
| **Processing pipeline performance** | Medium | Medium | Implement progress indicators; optimize chunking |
| **Local AI resource usage** | Medium | Medium | Recommend minimum specs; implement graceful degradation |
| **Cross-platform compatibility** | Low | High | Test on macOS, Windows, Linux throughout development |
| **Browser extension store approval** | Low | Medium | Follow Chrome Web Store guidelines strictly |

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

### Chat
```
POST   /api/conversations                    Create conversation
GET    /api/conversations                    List conversations
GET    /api/conversations/{id}               Get conversation with messages
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
