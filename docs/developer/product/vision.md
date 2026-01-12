# Product Vision

Cortex is a local-first, AI-powered personal knowledge management system.

## What Cortex Does

Cortex acts as an external brain that:

1. **Captures** content from your browser, files, and quick notes with zero friction
2. **Processes** everything using AI to extract meaning, not just keywords
3. **Connects** related ideas across sources and time automatically
4. **Retrieves** knowledge through natural conversation, not folder hierarchies

## The Problem

Knowledge workers are drowning in information scattered across dozens of tools. You save an insightful article, highlight a key passage in a book, bookmark a useful tweet—and then never find it again when you actually need it.

Current solutions fall short:

| Solution Type | Examples | Limitation |
|---------------|----------|------------|
| Note apps | Notion, Obsidian | Require manual organization, don't understand content |
| Read-later apps | Pocket, Instapaper | Become graveyards of unread articles |
| AI assistants | ChatGPT, Claude | No memory of what you've learned |
| Cloud PKM | Mem, Reflect | Require trusting a third party with personal thoughts |

## Why Local-First

The decision to build Cortex as a local-first application is foundational:

| Concern | Cloud-Only Approach | Our Local-First Approach |
|---------|---------------------|--------------------------|
| **Privacy** | Your thoughts on someone else's server | Your data never leaves your device |
| **Ownership** | Company shuts down, data at risk | Single SQLite file you control forever |
| **Cost** | Ongoing subscription fees | One-time purchase, minimal ongoing costs |
| **Latency** | Network round-trips for every action | Instant, works offline |
| **Trust** | "We won't read your data" promises | Mathematically impossible to access |

For a "second brain" containing your private thoughts, research, and sensitive information, local-first isn't just a feature—it's the only ethical choice.

## The Hybrid AI Option

While data always stays local, users can optionally use cloud AI providers for inference:

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Device                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Knowledge Base (SQLite)                             │    │
│  │  • Items, chunks, embeddings                         │    │
│  │  • Connections, conversations                        │    │
│  │  • NEVER leaves your device                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AI Processing                                       │    │
│  │  ┌─────────────┐         ┌─────────────┐            │    │
│  │  │   Ollama    │   OR    │  Cloud API  │            │    │
│  │  │   (Local)   │         │  (Optional) │            │    │
│  │  └─────────────┘         └─────────────┘            │    │
│  │                                  │                   │    │
│  │                     Only text being processed        │    │
│  │                     is sent (not your KB)            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

This is for users with limited hardware or those who want more capable models. Even then, only the text being processed is sent—your knowledge base, history, and connections remain on your machine.

## Core Principles

### 1. Privacy by Default

- All data stored locally in a single SQLite file
- No accounts, no cloud sync, no telemetry
- Cloud AI is opt-in, never required

### 2. Speed Over Features

- The app must feel instant
- No loading spinners for basic operations
- Background processing for AI-heavy tasks

### 3. Keyboard-First

- Power users live on the keyboard
- Every action has a shortcut
- Command palette for discoverability

### 4. Information Density

- Show more, scroll less
- This is a productivity tool, not a social app
- Progressive disclosure: simple by default, powerful when needed

### 5. AI as Enhancement, Not Replacement

- AI helps you find and connect, doesn't think for you
- Always shows sources and citations
- You control what gets processed and how

## Target Users

**Primary**: Knowledge workers who:
- Save content frequently (articles, papers, notes)
- Value privacy and data ownership
- Want AI assistance without cloud dependency
- Are comfortable with slightly technical setup (Ollama)

**Secondary**: Researchers, writers, and students who:
- Need to organize large amounts of information
- Want semantic search over keyword search
- Appreciate citation and source tracking

## What Cortex Is NOT

- **Not a note-taking app**: Obsidian/Notion are better for writing. Cortex is for capturing and retrieving.
- **Not a bookmark manager**: Raindrop/Pinboard are simpler. Cortex understands content deeply.
- **Not a cloud service**: No sync, no collaboration (yet). Local-first means local.
- **Not a general AI assistant**: Cortex only knows what you've saved. That's the point.
