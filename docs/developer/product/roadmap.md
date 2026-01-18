# Product Roadmap

Future features and expansion plans for Cortex.

## Current Focus

The initial release focuses on the core loop:

```
Capture → Process → Search → Chat
```

Everything else builds on this foundation.

## Post-Launch Features

### Tier 1: High Priority

Features that directly enhance the core experience.

#### PDF Support

- Parse and chunk PDF documents
- OCR for scanned pages (via Tesseract or similar)
- Preserve document structure (headings, sections)
- Handle multi-column layouts

**Why high priority**: PDFs are everywhere—research papers, ebooks, reports. Without PDF support, a significant portion of knowledge is inaccessible.

#### Audio/Video Transcription

- Transcribe podcasts and videos via Whisper (local)
- Support common formats (MP3, MP4, M4A, WAV)
- Timestamp-linked chunks for navigation
- Speaker diarization (future enhancement)

**Why high priority**: Podcasts and video content are increasingly important knowledge sources. Transcription makes them searchable.

#### Mobile Companion App

- React Native app for iOS/Android
- Capture on the go (share sheet integration)
- Sync via local network (no cloud)
- Read-only access to knowledge base
- Quick note capture

**Why high priority**: Ideas happen everywhere. Mobile capture removes friction.

#### Firefox & Safari Extensions

- Port Chrome extension to Firefox
- Safari extension for macOS users
- Maintain feature parity across browsers

**Why high priority**: Browser diversity matters. Chrome-only limits adoption.

### Tier 2: Differentiating Features

Features that set Cortex apart from alternatives.

#### Writing Assistant

- Surface relevant knowledge while you write
- Integrates with text editors (VS Code, Obsidian)
- "What do I know about X?" without leaving your editor
- Citation insertion

**Implementation approach**: Background service that monitors clipboard or editor content, suggests relevant items.

#### Smart Collections

- Auto-updating folders based on search queries
- "All items about machine learning from 2024"
- Saved searches that stay current
- Combine multiple criteria (topic + source + date)

**Implementation approach**: Stored queries that re-execute on new items. UI for building complex filters.

#### Graph Visualization

- See connections between items visually
- Interactive node graph
- Filter by connection type or strength
- Identify clusters and themes

**Implementation approach**: D3.js or similar for rendering. Compute graph layout on demand.

#### Bidirectional Sync (Optional)

- Export to Obsidian vault format
- Import from Notion exports
- Sync with Readwise (for highlights)
- User-controlled, not automatic

**Implementation approach**: Explicit export/import actions. No background sync to maintain local-first principles.

### Tier 3: Expansion

Features for growth and advanced use cases.

#### Team Features

- Share collections with teammates
- Still local-first: encrypted sync between devices
- No central server, peer-to-peer or self-hosted relay
- Granular permissions

**Complexity**: High. Requires solving distributed sync without compromising privacy.

#### Plugins API

- Let users extend capture sources
- Custom processing pipelines
- Third-party integrations
- Sandboxed execution

**Complexity**: High. API design, security model, documentation.

#### Custom Models

- Support for fine-tuned models on user's data
- Train embeddings on your vocabulary
- Fully local, no data leaves device
- For power users with specific domains

**Complexity**: High. Training infrastructure, model management, significant compute requirements.

## Feature Prioritization Framework

When deciding what to build next, consider:

| Factor                   | Weight    | Questions                                           |
| ------------------------ | --------- | --------------------------------------------------- |
| **Core loop impact**     | High      | Does it improve capture, process, search, or chat?  |
| **User requests**        | High      | Are users asking for this?                          |
| **Privacy preservation** | Must-have | Can we build this without compromising local-first? |
| **Technical complexity** | Medium    | How long will it take? What are the risks?          |
| **Differentiation**      | Medium    | Does this set us apart from alternatives?           |

## What We're NOT Building

To stay focused, some features are explicitly out of scope:

- **Real-time collaboration**: Conflicts with local-first. Use other tools for this.
- **Cloud sync service**: If you want cloud, use Notion/Mem. We're different.
- **Social features**: No sharing, no public profiles, no discovery.
- **Mobile-first**: Desktop is primary. Mobile is companion only.
- **AI writing**: Cortex retrieves and cites. It doesn't write for you.

## Versioning Strategy

- **Major versions (1.0, 2.0)**: New core capabilities
- **Minor versions (1.1, 1.2)**: New features within existing capabilities
- **Patch versions (1.1.1)**: Bug fixes and small improvements

The initial public release will be **1.0** with the core loop complete.
