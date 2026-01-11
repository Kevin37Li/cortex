# Cortex Development Plan
## A Local-First AI-Powered Second Brain

---

## Executive Summary

Cortex is a desktop application that acts as your personal knowledge management system. It captures content from anywhere, understands it deeply using AI, connects related ideas automatically, and surfaces relevant knowledge when you need it.

**What makes Cortex different:**
- **Local-First**: All data stays on your machine, AI runs locally by default
- **Privacy-First**: No accounts, no cloud sync, no data collection
- **Flexible AI**: Local models (Ollama) or cloud APIs (OpenAI, Anthropic, Google) — user's choice
- **Intelligent**: Semantic search, conversational retrieval, and automatic organization
- **Cross-Platform**: Runs on macOS, Windows, and Linux

---

## Part 1: Product Vision

### The Problem

Knowledge workers are drowning in information scattered across dozens of tools. You save an insightful article, highlight a key passage in a book, bookmark a useful tweet—and then never find it again when you actually need it.

Current solutions fall short:
- **Note apps** (Notion, Obsidian) require manual organization and don't understand your content
- **Read-later apps** (Pocket, Instapaper) are graveyards of unread articles
- **AI assistants** (ChatGPT, Claude) have no memory of what you've learned
- **Cloud-based PKM** (Mem, Reflect) require trusting a third party with your most personal thoughts

### The Solution

Cortex acts as an external brain that:

1. **Captures** content from your browser, files, and quick notes with zero friction
2. **Processes** everything using local AI to extract meaning, not just keywords
3. **Connects** related ideas across sources and time automatically
4. **Retrieves** knowledge through natural conversation, not folder hierarchies

### Why Local-First?

The decision to build Cortex as a local-first application is foundational to the product:

| Concern | Cloud-Only Approach | Our Local-First Approach |
|---------|---------------------|--------------------------|
| **Privacy** | Your thoughts on someone else's server | Your data never leaves your device |
| **Ownership** | Company shuts down, data at risk | Single SQLite file you control forever |
| **Cost** | Ongoing subscription fees | One-time purchase, minimal ongoing costs |
| **Latency** | Network round-trips for every action | Instant, works offline |
| **Trust** | "We won't read your data" promises | Mathematically impossible to access |

For a "second brain" containing your private thoughts, research, and sensitive information, local-first isn't just a feature—it's the only ethical choice.

**The Hybrid Option**: While data always stays local, users can optionally use cloud AI providers (OpenAI, Anthropic, Google) for inference. This is for users with limited hardware or those who want more capable models. Even then, only the text being processed is sent — your knowledge base, history, and connections remain on your machine.

---

## Part 2: Architecture Decisions

### Technology Stack Summary

| Layer | Technology | Why |
|-------|------------|-----|
| **Desktop Shell** | Tauri 2.0 (Rust) | Small binary, native performance, secure |
| **Frontend** | React + TypeScript + Vite | Fast dev, great ecosystem, type safety |
| **UI Components** | shadcn/ui + Tailwind | Beautiful defaults, rapid development |
| **Backend** | Python + FastAPI | AI ecosystem, LangGraph support |
| **Database** | SQLite + sqlite-vec | Single file, zero config, vector search built-in |
| **AI Orchestration** | LangGraph | Stateful workflows, retries, cycles |
| **Local AI** | Ollama | Easy model management, runs anywhere |
| **Cloud AI** | LiteLLM → OpenAI/Anthropic/Google | Unified interface, direct API pricing |
| **Browser Extension** | Plasmo | Modern DX, cross-browser |

### Decision 1: Tauri + Python Sidecar

**What**: A Tauri desktop shell (Rust + React) that spawns a Python backend process.

**Why this hybrid approach:**

The obvious choice for a local AI app would be Electron + Node.js, but this has significant drawbacks:
- Electron apps are bloated (150MB+ just for the shell)
- Node.js lacks mature ML/AI libraries
- Python has the best ecosystem for LangChain, LangGraph, and AI tooling

Pure Rust would be ideal for performance, but:
- Rust has a steep learning curve
- The LangGraph ecosystem is Python-first
- Rapid iteration is harder in Rust

**Our solution** gets the best of both worlds:

```
┌─────────────────────────────────────┐
│         Tauri Shell (Rust)          │  ← Small, fast, native
│  • Window management                │
│  • System tray                      │
│  • File system access               │
│  • IPC bridge to Python             │
└──────────────────┬──────────────────┘
                   │ localhost HTTP
┌──────────────────▼──────────────────┐
│      Python Sidecar (FastAPI)       │  ← All the AI magic
│  • LangGraph workflows              │
│  • SQLite database                  │
│  • Ollama integration               │
└─────────────────────────────────────┘
```

**Trade-offs accepted:**
- Two runtimes instead of one (acceptable: Python is usually already installed)
- Slightly more complex deployment (mitigated: we bundle Python with the app)
- IPC overhead (negligible: localhost HTTP is fast)

### Decision 2: SQLite + sqlite-vec for Storage

**What**: A single SQLite database file with the sqlite-vec extension for vector search.

**Why SQLite:**

For a local-first app, SQLite is the obvious choice:
- Zero configuration, no separate database server
- Battle-tested reliability (used in every iPhone, Android, browser)
- Single file that users can backup, move, or inspect
- Excellent performance for our scale (millions of chunks is fine)

**Why sqlite-vec over alternatives:**

| Option | Pros | Cons |
|--------|------|------|
| Pinecone/Weaviate | Powerful, scalable | Cloud-based, defeats local-first purpose |
| ChromaDB | Local, popular | Separate process, adds complexity |
| pgvector | Great for Postgres | Requires PostgreSQL server |
| **sqlite-vec** | Native SQLite extension, single file | Newer, smaller community |

sqlite-vec keeps everything in one file—your items, chunks, embeddings, and conversations all live together. This dramatically simplifies backup, sync, and portability.

**Data model overview:**

```
cortex.db
├── items          → Saved content (webpages, notes, PDFs)
├── chunks         → Semantic segments of each item
├── embeddings     → Vector representations (sqlite-vec virtual table)
├── connections    → Discovered relationships between items
├── conversations  → Chat history
└── messages       → Individual chat messages with citations
```

### Decision 3: Ollama + Direct APIs for AI

**What**: Ollama provides local AI inference by default. Direct cloud APIs (OpenAI, Anthropic, Google) are available as an alternative for users who need them.

**Why this hybrid approach:**

Local-first with Ollama:
- **Privacy maximum**: Nothing leaves the device
- **Works offline**: No internet required
- **Zero ongoing cost**: Just your electricity
- **User controls models**: Swap based on hardware and needs

But local models have real limitations:
- Require decent hardware (8GB+ RAM for usable models)
- Quality gap vs frontier models (GPT-4, Claude 3.5)
- Slower on CPU-only machines

**The solution**: Offer direct cloud APIs as a complement, not a replacement.

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Provider Layer                         │
│                                                              │
│  ┌─────────────────────┐      ┌─────────────────────────┐   │
│  │       Ollama        │      │     Direct APIs         │   │
│  │      (Default)      │      │    (Alternative)        │   │
│  │                     │      │                         │   │
│  │  • Maximum privacy  │      │  • OpenAI               │   │
│  │  • Works offline    │      │  • Anthropic            │   │
│  │  • Free             │      │  • Google               │   │
│  │  • Needs 8GB+ RAM   │      │  • User provides keys   │   │
│  └──────────┬──────────┘      └────────────┬────────────┘   │
│             └──────────────┬───────────────┘                │
│                            │                                 │
│                 ┌──────────▼──────────┐                     │
│                 │  Unified Interface   │                     │
│                 │  embed() / chat()    │                     │
│                 └──────────┬──────────┘                     │
│                            │                                 │
└────────────────────────────┼────────────────────────────────┘
                             │
                  LangGraph Workflows
```

**Why direct APIs over aggregators (OpenRouter, etc.):**

| Factor | Aggregators | Direct APIs |
|--------|-------------|-------------|
| **Reliability** | Middleman can fail | Only provider uptime matters |
| **Longevity** | Startup risk | OpenAI/Anthropic/Google aren't going anywhere |
| **Pricing** | 5-20% markup | Base price |
| **Complexity** | One API key | Multiple keys (but LiteLLM abstracts this) |

For a desktop app meant to last years, depending on a VC-funded aggregator is unnecessary risk. LiteLLM (open source, bundled locally) gives us unified API access without the middleman.

**Model recommendations:**

| Use Case | Ollama (Local) | Cloud Alternative |
|----------|---------------|-------------------|
| **Embeddings** | nomic-embed-text (274MB) | OpenAI text-embedding-3-small |
| **Chat (Budget)** | llama3.2:3b (2GB) | Google Gemini 1.5 Flash |
| **Chat (Quality)** | mistral:7b (4GB) | Anthropic Claude 3 Haiku |
| **Chat (Best)** | llama3.1:70b (40GB) | Claude 3.5 Sonnet / GPT-4o |

**Typical cloud costs** (for users who choose that path):
- Light usage (50 items/month): ~$0.10-0.25/month
- Heavy usage (200 items/month): ~$0.50-1.00/month
- Using premium models (Sonnet/GPT-4o): ~$2-5/month

### Decision 4: LangGraph for AI Workflows

**What**: LangGraph orchestrates multi-step AI operations as directed graphs with state management.

**Why we need workflow orchestration:**

A Second Brain has complex AI operations that aren't simple request-response:

1. **Processing a saved article:**
   - Parse HTML → Chunk semantically → Embed each chunk → Extract metadata → Validate quality → Retry if poor → Store results → Discover connections

2. **Searching your knowledge:**
   - Analyze query intent → Decompose if complex → Vector search → Full-text search → Fuse results → Evaluate relevance → Expand query if poor → Return results

3. **Chatting with your knowledge:**
   - Retrieve context → Grade document relevance → Rewrite query if needed → Generate answer → Check if grounded in sources → Regenerate if hallucinating

These aren't single LLM calls—they're stateful workflows with branching logic, retry loops, and quality gates.

**Why LangGraph specifically:**

| Alternative | Issue |
|-------------|-------|
| Plain functions | State management becomes spaghetti, no visibility |
| Celery/queue systems | Overkill for local, adds infrastructure |
| LangChain alone | Chains are linear, can't handle cycles |
| Custom state machine | Reinventing the wheel |

LangGraph provides:
- **Typed state**: Each workflow has a clear schema
- **Conditional edges**: Route to different nodes based on state
- **Cycles**: Naturally handle retry loops
- **Checkpointing**: Resume interrupted workflows (important for large imports)
- **Debuggability**: Visualize execution, trace issues

### Decision 5: React Frontend with TypeScript

**What**: The UI is a React application running in Tauri's webview.

**Why React:**

- Largest ecosystem of components (shadcn/ui gives us beautiful defaults)
- You likely already know it
- Excellent TypeScript support
- Works seamlessly with Tauri

**Key UI principles:**

1. **Speed over features**: The app must feel instant. No loading spinners for basic operations.
2. **Keyboard-first**: Power users live on the keyboard. Every action has a shortcut.
3. **Information density**: Show more, scroll less. This is a productivity tool, not a social app.
4. **Progressive disclosure**: Simple by default, powerful when needed.

---

### Decision 6: AI Provider Architecture

**What**: A unified provider interface that abstracts Ollama and direct cloud APIs behind a common API.

**Why this matters:**

Users have different needs:
- Privacy maximalists want everything local
- Users with weak hardware need cloud inference
- Power users want the best models regardless of where they run

The app shouldn't care which provider is used — LangGraph workflows call `embed()` and `chat()` without knowing if it's Ollama or Claude.

**Implementation approach:**

```python
# All providers implement this interface
class AIProvider:
    async def embed(text: str) -> list[float]
    async def embed_batch(texts: list[str]) -> list[list[float]]
    async def chat(messages: list, system: str) -> str
    async def stream_chat(messages: list) -> AsyncIterator[str]
```

**LiteLLM for cloud APIs:**

Rather than implementing separate clients for OpenAI, Anthropic, and Google, we use LiteLLM — an open-source library that provides a unified interface to 100+ LLM providers. It runs locally (bundled with the app), so there's no middleman service.

Benefits of LiteLLM:
- Single interface for all providers
- Automatic retries and fallbacks
- Cost tracking built-in
- User just provides their API keys

**User experience flow:**

```
First Launch
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  How would you like Cortex to process your content?         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  🏠 Local AI (Recommended)                              │ │
│  │                                                          │ │
│  │  Everything runs on your machine using Ollama.          │ │
│  │  Maximum privacy — nothing leaves your computer.        │ │
│  │                                                          │ │
│  │  Requirements: 8GB RAM minimum, 16GB recommended        │ │
│  │  Cost: Free                                              │ │
│  │                                                          │ │
│  │                                    [Set Up Ollama →]    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ☁️ Cloud AI                                            │ │
│  │                                                          │ │
│  │  Use OpenAI, Anthropic, or Google for AI processing.   │ │
│  │  Better for older hardware or when you need top models. │ │
│  │                                                          │ │
│  │  Requirements: API key(s), internet connection          │ │
│  │  Cost: ~$0.10-1.00/month typical usage                  │ │
│  │                                                          │ │
│  │                                   [Configure APIs →]    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  🔀 Hybrid                                              │ │
│  │                                                          │ │
│  │  Use local AI by default, cloud for complex queries.   │ │
│  │  Best of both worlds.                                   │ │
│  │                                                          │ │
│  │                                    [Set Up Both →]      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ℹ️ Your data always stays on your device.                  │
│    Only the text being processed is sent to cloud APIs.    │
│    You can change this anytime in Settings.                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Settings UI for cloud APIs:**

```
┌─────────────────────────────────────────────────────────────┐
│  AI Provider Settings                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Current Mode: ● Local (Ollama)  ○ Cloud  ○ Hybrid          │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│  Local AI (Ollama)                          Status: Running │
│  ─────────────────────────────────────────────────────────  │
│  Embedding Model    [nomic-embed-text              ▼]       │
│  Chat Model         [llama3.2:3b                   ▼]       │
│                                                              │
│  [Download More Models]                                      │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│  Cloud APIs (Optional)                                       │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  OpenAI        [sk-proj-••••••••••••••]    ✓ Connected      │
│  Anthropic     [Not configured]             [Add Key]        │
│  Google        [Not configured]             [Add Key]        │
│                                                              │
│  Cloud Model Preferences:                                    │
│  Embeddings     [openai/text-embedding-3-small     ▼]       │
│  Chat           [anthropic/claude-3-haiku          ▼]       │
│                                                              │
│  ☑ Enable fallback (if primary provider fails, try others)  │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│  Usage This Month                                            │
│  ─────────────────────────────────────────────────────────  │
│  Local:  1,247 queries                                       │
│  Cloud:  23 queries │ ~$0.04 estimated                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Hybrid mode behavior:**

When hybrid mode is enabled:
1. **Embeddings**: Always use the configured embedding provider (usually local for speed)
2. **Simple extraction**: Use local model
3. **Complex chat queries**: User can choose per-query or set a default
4. **Fallback**: If local model fails or is unavailable, fall back to cloud

This gives users fine-grained control while keeping the default experience simple.

---

## Part 3: LangGraph Workflows

### Workflow 1: Content Processing

**Purpose**: Transform raw saved content into searchable, connected knowledge.

**Flow:**

```
┌─────────────┐
│  New Item   │ User saves a webpage, uploads a PDF, or writes a note
└──────┬──────┘
       │
┌──────▼──────┐
│  Classify   │ Determine content type to route to appropriate parser
└──────┬──────┘
       │
   ┌───┴───┐───────┐
   ▼       ▼       ▼
┌──────┐┌──────┐┌──────┐
│ HTML ││ PDF  ││Audio │ Parse into clean text (different strategies per type)
└──┬───┘└──┬───┘└──┬───┘
   └───┬───┘───────┘
       │
┌──────▼──────┐
│   Chunk     │ Split into semantic segments (not fixed-size)
└──────┬──────┘ Preserve paragraph boundaries, add overlap
       │
┌──────▼──────┐
│   Embed     │ Generate vector embedding for each chunk
└──────┬──────┘ Batch process through Ollama
       │
┌──────▼──────┐
│  Extract    │ Use LLM to extract structured metadata:
└──────┬──────┘ - Summary (short and long)
       │        - Key concepts
       │        - Named entities (people, companies, products)
       │        - Questions this content answers
       │
┌──────▼──────┐      ┌──────────────┐
│  Validate   │─────▶│    Retry     │ If extraction quality is poor,
└──────┬──────┘ Poor └──────┬───────┘ retry with different prompt
       │ Good              │
       │◀──────────────────┘
       │
┌──────▼──────┐
│   Store     │ Persist chunks, embeddings, and metadata
└──────┬──────┘
       │
┌──────▼──────┐
│  Connect    │ Find related items via embedding similarity
└─────────────┘ Store bidirectional connections
```

**Why this design:**

- **Conditional parsing**: PDFs need OCR, audio needs transcription, HTML needs cleanup. One-size-fits-all fails.
- **Semantic chunking**: Fixed-size chunks (e.g., 500 tokens) break mid-sentence. Semantic chunking respects document structure.
- **Extraction validation**: LLMs sometimes produce garbage. A validation step catches obvious failures.
- **Async connection discovery**: Finding connections is slow but not urgent. Run it after the user gets their "saved!" confirmation.

### Workflow 2: Adaptive Search

**Purpose**: Find relevant content even when the user's query is vague or complex.

**Flow:**

```
┌─────────────┐
│   Query     │ "What do I know about pricing strategies for B2B SaaS?"
└──────┬──────┘
       │
┌──────▼──────┐
│  Analyze    │ Classify query complexity:
└──────┬──────┘ - Simple: direct lookup ("machine learning basics")
       │        - Multi-faceted: multiple aspects ("React vs Vue for large projects")
       │        - Temporal: time-based ("articles from last month")
       │
   ┌───┴────────────┐
   │ Multi-faceted  │
   ▼                │
┌──────────┐        │
│Decompose │        │ Break into sub-queries:
└────┬─────┘        │ - "B2B SaaS pricing models"
     │              │ - "pricing psychology"
     │              │ - "value-based pricing"
     ▼              │
┌─────────────◀─────┘
│Vector Search│ Embed query, find similar chunks
└──────┬──────┘
       │
┌──────▼──────┐
│  FTS Search │ Full-text search for exact phrases, names
└──────┬──────┘
       │
┌──────▼──────┐
│    Fuse     │ Reciprocal Rank Fusion combines both result sets
└──────┬──────┘ Items appearing in both rank higher
       │
┌──────▼──────┐      ┌──────────────┐
│  Evaluate   │─────▶│   Expand     │ If results are poor,
└──────┬──────┘ Poor └──────┬───────┘ add synonyms/related terms
       │ Good              │
       │◀──────────────────┘
       │
┌──────▼──────┐
│   Return    │ Ranked results with matched snippets
└─────────────┘
```

**Why this design:**

- **Hybrid search**: Vector search finds conceptually similar content. Full-text search finds exact matches. Neither alone is sufficient.
- **Query decomposition**: Complex queries often need multiple searches. "Compare X and Y" should search for both X and Y.
- **Automatic expansion**: If the first search returns nothing useful, try related terms before giving up.
- **RRF fusion**: A simple but effective algorithm for combining ranked lists. Items that appear in multiple searches are more likely relevant.

### Workflow 3: RAG Chat

**Purpose**: Answer questions using your personal knowledge base with citations.

**Flow:**

```
┌─────────────┐
│   Message   │ "What were the key insights from that pricing article?"
└──────┬──────┘
       │
┌──────▼──────┐
│  Retrieve   │ Search for relevant chunks (using Search workflow)
└──────┬──────┘
       │
┌──────▼──────┐
│   Grade     │ LLM evaluates each chunk: "Is this relevant to the question?"
└──────┬──────┘ Filter out tangentially related content
       │
   ┌───┴───────────────────┐
   │ No relevant docs      │
   ▼                       │
┌──────────┐               │
│ Rewrite  │               │ Transform query for better retrieval:
│  Query   │───────────────│ "pricing article insights" → 
└────┬─────┘  Retry search │ "pricing strategy key points summary"
     │                     │
     └─────────────────────┘
       │ Have relevant docs
       │
┌──────▼──────┐
│  Generate   │ Build prompt with context, generate answer
└──────┬──────┘ Include citations: "According to [Article Title]..."
       │
┌──────▼──────┐
│   Ground    │ Verify answer is supported by sources
└──────┬──────┘ Catch hallucinations before showing user
       │
   ┌───┴───────────────────┐
   │ Not grounded          │
   ▼                       │
┌──────────┐               │
│Regenerate│               │ Try again with stricter prompt
└────┬─────┘               │
     │                     │
     └─────────────────────┘
       │ Grounded
       │
┌──────▼──────┐
│   Return    │ Answer with citations to source items
└─────────────┘
```

**Why this design:**

- **Document grading**: Not all retrieved content is useful. Filtering before generation improves answer quality.
- **Query rewriting**: The user's natural question often isn't the best search query. Reformulating helps retrieval.
- **Grounding check**: Local LLMs hallucinate. A second pass catches answers that aren't supported by sources.
- **Citations**: Users need to verify AI answers. Always link back to the original content.

### Workflow 4: Connection Discovery

**Purpose**: Automatically find relationships between items in your knowledge base.

**Flow:**

```
┌─────────────┐
│ Item Ready  │ Triggered after processing completes
└──────┬──────┘
       │
┌──────▼──────┐
│Find Similar │ Vector search for items with similar embeddings
└──────┬──────┘ 
       │
┌──────▼──────┐
│  Extract    │ Get entities (people, companies, concepts) from this item
│  Entities   │
└──────┬──────┘
       │
┌──────▼──────┐
│   Match     │ Find other items mentioning the same entities
│  Entities   │ "This article mentions Stripe, you have 5 others about Stripe"
└──────┬──────┘
       │
┌──────▼──────┐
│  Temporal   │ Find items saved around the same time
│  Cluster    │ "You saved these 4 items the same week—likely related research"
└──────┬──────┘
       │
┌──────▼──────┐
│   Score     │ Assign connection strength (0-1) based on evidence
└──────┬──────┘ Multiple signals (similar + same entity) = stronger connection
       │
┌──────▼──────┐
│   Store     │ Save bidirectional connections above threshold
└─────────────┘
```

**Why this design:**

- **Multiple signals**: Similarity alone misses connections. Entity matching catches "different articles about the same company."
- **Temporal clustering**: What you saved together is often related. This captures research sessions.
- **Strength scoring**: Not all connections are equal. "Same author" is weaker than "same topic + same entities."
- **Background processing**: This runs after the user has moved on. Don't block the save confirmation.

### Workflow 5: Daily Digest

**Purpose**: Proactively surface insights and forgotten gems.

**Flow:**

```
┌─────────────┐
│  Scheduled  │ Runs daily (or weekly, user preference)
│   Trigger   │
└──────┬──────┘
       │
┌──────▼──────┐
│   Gather    │ Recent items (last 7 days)
│   Recent    │
└──────┬──────┘
       │
┌──────▼──────┐
│  Find New   │ Connections discovered since last digest
│ Connections │ "Your article on X relates to your note on Y"
└──────┬──────┘
       │
┌──────▼──────┐
│  Surface    │ High-value old items you haven't accessed
│   Gems      │ "6 months ago you saved this—still relevant?"
└──────┬──────┘
       │
┌──────▼──────┐
│  Generate   │ LLM creates insights across items:
│  Insights   │ "You've been researching pricing a lot. Key themes are..."
└──────┬──────┘
       │
┌──────▼──────┐
│  Compose    │ Format into readable digest
└──────┬──────┘
       │
┌──────▼──────┐
│   Notify    │ Show in app, optionally send to system notifications
└─────────────┘
```

**Why this design:**

- **Proactive value**: Users save content and forget it. The digest brings knowledge back.
- **Serendipity**: Surfacing old content creates unexpected connections.
- **Synthesis**: The LLM can see patterns across items that humans miss.
- **Respecting attention**: Daily is optional. Some users want weekly or manual-only.

---

## Part 4: Development Phases

### Phase 1: Foundation (Weeks 1-4)

**Goal**: A working app that can save and retrieve content with flexible AI backend.

**Deliverables:**
1. Tauri app shell with React frontend
2. Python sidecar with FastAPI
3. SQLite database with schema
4. AI Provider abstraction layer:
   - Ollama provider implementation
   - Direct API provider via LiteLLM (OpenAI, Anthropic, Google)
   - Unified interface for LangGraph workflows
5. Basic item CRUD (create, read, update, delete)
6. Provider selection onboarding flow
7. Simple item list UI

**Technical milestones:**
- [ ] Tauri spawns Python process on startup, manages lifecycle
- [ ] Frontend can call Python endpoints via localhost
- [ ] Items persist in SQLite and survive app restart
- [ ] Ollama provider works with health check and model verification
- [ ] LiteLLM provider works with at least one cloud API (OpenAI)
- [ ] User can switch providers in settings

**Why start here:**
The AI provider layer is foundational — every subsequent feature depends on it. Getting this right early prevents painful refactors later. Users should be able to choose their provider from day one.

### Phase 2: Processing Pipeline (Weeks 5-8)

**Goal**: Saved content is processed and searchable.

**Deliverables:**
1. Processing Graph (LangGraph) with:
   - HTML parsing and cleanup
   - Semantic chunking
   - Embedding generation via Ollama
   - Basic metadata extraction
2. Vector search via sqlite-vec
3. Full-text search via SQLite FTS5
4. Processing status UI (pending → processing → ready)

**Technical milestones:**
- [ ] Saving a webpage triggers processing automatically
- [ ] Embeddings stored in sqlite-vec and searchable
- [ ] Search returns relevant chunks with snippets
- [ ] Failed processing can be retried

**Why this phase:**
Search is the core value proposition. Without good retrieval, chat and connections don't work. This phase proves the AI pipeline functions.

### Phase 3: Browser Extension (Weeks 9-10)

**Goal**: Users can capture content from their browser with one click.

**Deliverables:**
1. Chrome extension (Firefox later)
   - Popup with "Save to Cortex" button
   - Content extraction from current page
   - Highlight capture
2. Local HTTP endpoint for extension communication
3. Keyboard shortcut support

**Technical milestones:**
- [ ] Extension detects running Cortex app
- [ ] One-click save extracts title, URL, content
- [ ] Highlighted text saved with context
- [ ] Works on major sites (articles, Twitter, YouTube)

**Why this phase:**
Capture friction kills adoption. If saving is hard, users won't build a knowledge base. The extension makes capture effortless.

### Phase 4: RAG Chat (Weeks 11-14)

**Goal**: Users can have conversations with their knowledge base.

**Deliverables:**
1. Chat Graph (LangGraph) with:
   - Context retrieval
   - Document grading
   - Query rewriting
   - Grounded generation
2. Chat UI with:
   - Conversation history
   - Citations linking to source items
   - Streaming responses
3. Conversation persistence

**Technical milestones:**
- [ ] Chat answers questions using saved content
- [ ] Citations are clickable and accurate
- [ ] Conversation history persists across sessions
- [ ] Response quality is acceptable with local models

**Why this phase:**
Chat is the primary interface for knowledge retrieval. It's more natural than search for many queries and demonstrates AI value clearly.

### Phase 5: Connections & Intelligence (Weeks 15-18)

**Goal**: The app proactively surfaces insights and connections.

**Deliverables:**
1. Connection Discovery Graph
2. Adaptive Search Graph with:
   - Query decomposition
   - Automatic expansion
3. Metadata extraction improvements:
   - Entity extraction
   - Concept tagging
4. "Related Items" sidebar in item view
5. Daily Digest (optional, user-enabled)

**Technical milestones:**
- [ ] Items show related content automatically
- [ ] Search handles complex queries gracefully
- [ ] Daily digest surfaces forgotten content
- [ ] Entity-based connections work (same person/company)

**Why this phase:**
Connections transform a "save and search" tool into a true Second Brain. This is where Cortex becomes meaningfully different from alternatives.

### Phase 6: Polish & Launch (Weeks 19-22)

**Goal**: Production-ready application.

**Deliverables:**
1. Onboarding flow with:
   - AI provider selection (Ollama vs Cloud vs Hybrid)
   - Ollama setup wizard with model downloads
   - API key configuration for cloud providers
2. Settings UI:
   - Model selection per task
   - Provider switching
   - Usage tracking and cost estimates
3. Import from existing tools (Pocket, Readwise export)
4. Export (Markdown, JSON backup)
5. Auto-updates via Tauri
6. Crash reporting and error handling
7. Performance optimization
8. Platform-specific builds (macOS, Windows, Linux)

**Technical milestones:**
- [ ] New user can go from download to first save in < 5 minutes
- [ ] Provider switching works without data loss
- [ ] App handles 10,000+ items without performance degradation
- [ ] Crash reports collected (locally) for debugging
- [ ] Signed builds for all platforms

**Why this phase:**
Polish separates a prototype from a product. Onboarding, updates, and error handling are invisible when done right but fatal when missing.

---

## Part 5: Technical Risks & Mitigations

### Risk 1: Local LLM Quality

**Concern**: Local models may produce poor extractions or answers compared to GPT-4/Claude.

**Mitigations:**
- Validation loops in workflows catch obvious failures
- Extraction prompts optimized for smaller models (simpler, more explicit)
- Users with powerful hardware can use larger local models (7B+)
- **Cloud API option**: Users who need quality can use direct APIs (Anthropic, OpenAI, Google)
- Clear guidance on which tasks benefit most from better models

### Risk 2: Ollama Dependency

**Concern**: Requiring users to install Ollama adds friction.

**Mitigations:**
- Clear onboarding wizard with one-click Ollama install
- App detects missing Ollama and guides user through setup
- Future option: bundle llama.cpp directly (no external dependency)

### Risk 3: sqlite-vec Maturity

**Concern**: sqlite-vec is newer than alternatives like ChromaDB.

**Mitigations:**
- Extensive testing with realistic data volumes
- Fallback plan: migrate to ChromaDB if issues arise (similar API)
- sqlite-vec is actively maintained and used in production by others

### Risk 4: Cross-Platform Python Bundling

**Concern**: Shipping Python with a desktop app is complex.

**Mitigations:**
- PyInstaller or PyOxidizer creates standalone executable
- Tauri's sidecar feature handles process management
- Test extensively on all platforms before each release

### Risk 5: Processing Performance

**Concern**: Embedding many chunks is slow with local models.

**Mitigations:**
- Batch embedding reduces Ollama overhead
- Background processing doesn't block UI
- Progress indicators keep users informed
- "Process later" option for bulk imports

---

## Part 6: Future Roadmap (Post-Launch)

### Tier 1: High Priority Additions

1. **PDF Support**: Parse and chunk PDF documents, OCR for scanned pages
2. **Audio/Video**: Transcribe podcasts and videos via Whisper
3. **Mobile Companion**: React Native app for capture on the go (syncs via local network)
4. **More Browsers**: Firefox and Safari extensions

### Tier 2: Differentiating Features

1. **Writing Assistant**: Surface relevant knowledge while you write (integrates with editors)
2. **Smart Collections**: Auto-updating folders based on search queries
3. **Graph Visualization**: See connections between items visually
4. **Bi-directional Sync**: Optional integration with Notion, Obsidian (user-controlled)

### Tier 3: Expansion

1. **Team Features**: Share collections with teammates (still local-first, encrypted sync)
2. **Plugins API**: Let users extend capture and processing
3. **Custom Models**: Support for fine-tuned models on user's data (fully local)

---

## Part 7: Success Metrics

### User Success

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Items captured per week | 10+ | Measures habit formation |
| Search queries per week | 5+ | Proves retrieval value |
| Chat sessions per week | 3+ | Shows AI is useful |
| 30-day retention | 40%+ | Real stickiness |

### Technical Health

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Processing success rate | 95%+ | Pipeline reliability |
| Search latency (p95) | < 500ms | Feels instant |
| Chat response time | < 5s | Acceptable for local LLM |
| App crash rate | < 1% | Stability |

### Business (If Monetized)

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Downloads | 10K in 6 months | Market validation |
| Paid conversions | 5%+ | Sustainable business |
| Refund rate | < 5% | Product satisfaction |

---

## Conclusion

Cortex is a bet on three trends:

1. **Privacy backlash**: Users increasingly want their data local, not in the cloud
2. **Local AI maturity**: Open-source models are finally good enough for real applications
3. **Knowledge overload**: The problem of fragmented information is getting worse, not better

By combining a local-first architecture with LangGraph-orchestrated AI workflows and flexible provider options, we can build a Second Brain that's private by default, intelligent, and accessible to users regardless of their hardware.

**The key insight**: Data locality and AI capability don't have to be at odds. Your knowledge base stays on your machine always. Only the AI inference is flexible — run it locally for maximum privacy, or use cloud APIs when you need more power. Users choose their own trade-off.

The path from here to launch is clear:
1. Build the foundation (Tauri + Python + SQLite + Provider Layer)
2. Prove the AI works (Processing + Search)
3. Make capture effortless (Browser Extension)
4. Deliver the magic (Chat + Connections)
5. Polish and ship

Let's build the knowledge tool we wish existed.

---

*Development Plan Version: 2.0 (Ollama + Direct APIs)*
*Last Updated: December 2024*
