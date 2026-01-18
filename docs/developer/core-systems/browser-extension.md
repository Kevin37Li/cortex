# Browser Extension

Capture content from the browser with one click.

## Overview

The browser extension enables frictionless content capture:

- Save entire pages or selected text
- Extract clean content from articles
- Capture highlights with context
- Works offline (queues until desktop app is running)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Extension                         │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Popup UI      │  │ Content Script  │  │  Background │ │
│  │                 │  │                 │  │   Worker    │ │
│  │  • Save button  │  │  • DOM access   │  │             │ │
│  │  • Status       │  │  • Selection    │  │  • Storage  │ │
│  │  • Settings     │  │  • Extraction   │  │  • Queue    │ │
│  └────────┬────────┘  └────────┬────────┘  │  • Sync     │ │
│           │                    │           └──────┬──────┘ │
│           └────────────────────┴──────────────────┘        │
│                                │                            │
└────────────────────────────────┼────────────────────────────┘
                                 │ localhost:8742
                                 │
┌────────────────────────────────▼────────────────────────────┐
│                    Cortex Desktop App                        │
│                    (Python Backend)                          │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component              | Technology                         | Why                                  |
| ---------------------- | ---------------------------------- | ------------------------------------ |
| **Framework**          | [Plasmo](https://docs.plasmo.com/) | Modern DX, TypeScript, cross-browser |
| **UI**                 | React + Tailwind                   | Consistent with desktop app          |
| **State**              | Zustand                            | Lightweight, same pattern as desktop |
| **Content Extraction** | @mozilla/readability               | Battle-tested article parsing        |

## Project Structure

```
browser-extension/
├── src/
│   ├── popup/              # Popup UI
│   │   ├── index.tsx
│   │   └── components/
│   │
│   ├── contents/           # Content scripts
│   │   ├── capture.ts      # Main capture logic
│   │   └── highlight.ts    # Text selection handling
│   │
│   ├── background/         # Service worker
│   │   ├── index.ts
│   │   ├── queue.ts        # Offline queue
│   │   └── sync.ts         # Desktop communication
│   │
│   ├── lib/
│   │   ├── extractor.ts    # Content extraction
│   │   ├── api.ts          # Desktop API client
│   │   └── storage.ts      # Extension storage
│   │
│   └── assets/
│       └── icon.png
│
├── package.json
├── plasmo.config.ts
└── tailwind.config.js
```

## Core Features

### 1. Full Page Capture

Save the entire current page:

```typescript
// src/contents/capture.ts
import { Readability } from '@mozilla/readability'

export async function captureFullPage(): Promise<CapturedContent> {
  const doc = document.cloneNode(true) as Document

  // Use Readability to extract article content
  const reader = new Readability(doc)
  const article = reader.parse()

  return {
    url: window.location.href,
    title: article?.title || document.title,
    content: article?.content || document.body.innerHTML,
    textContent: article?.textContent || document.body.textContent,
    excerpt: article?.excerpt,
    byline: article?.byline,
    siteName: article?.siteName,
    capturedAt: new Date().toISOString(),
  }
}
```

### 2. Selection Capture

Save highlighted text with surrounding context:

```typescript
// src/contents/highlight.ts
export function captureSelection(): CapturedSelection | null {
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed) return null

  const range = selection.getRangeAt(0)

  // Get surrounding context (paragraph or nearby text)
  const container = range.commonAncestorContainer
  const contextNode =
    container.nodeType === Node.TEXT_NODE
      ? container.parentElement
      : (container as Element)

  return {
    selectedText: selection.toString(),
    context: contextNode?.textContent || '',
    url: window.location.href,
    title: document.title,
    capturedAt: new Date().toISOString(),
  }
}
```

### 3. Quick Notes

Add a note without leaving the page:

```typescript
// In popup
export function QuickNoteForm() {
  const [note, setNote] = useState('')

  const handleSave = async () => {
    await sendToDesktop({
      type: 'note',
      content: note,
      url: currentTab.url,
      title: `Note on: ${currentTab.title}`,
    })
  }

  return (
    <textarea
      value={note}
      onChange={(e) => setNote(e.target.value)}
      placeholder="Add a note about this page..."
    />
  )
}
```

## Desktop Communication

### API Client

```typescript
// src/lib/api.ts
const DESKTOP_URL = 'http://localhost:8742'

export async function sendToDesktop(
  content: CapturedContent
): Promise<SaveResult> {
  try {
    const response = await fetch(`${DESKTOP_URL}/api/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: content.url,
        title: content.title,
        content: content.content,
        source: 'browser_extension',
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    return { success: true, itemId: (await response.json()).id }
  } catch (error) {
    // Desktop not running - queue for later
    await queueForLater(content)
    return { success: false, queued: true }
  }
}

export async function checkDesktopStatus(): Promise<boolean> {
  try {
    const response = await fetch(`${DESKTOP_URL}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(2000),
    })
    return response.ok
  } catch {
    return false
  }
}
```

### Offline Queue

When desktop app isn't running, queue captures locally:

```typescript
// src/background/queue.ts
interface QueuedItem {
  id: string
  content: CapturedContent
  createdAt: string
  attempts: number
}

export async function queueForLater(content: CapturedContent): Promise<void> {
  const queue = await getQueue()
  queue.push({
    id: crypto.randomUUID(),
    content,
    createdAt: new Date().toISOString(),
    attempts: 0,
  })
  await chrome.storage.local.set({ captureQueue: queue })
}

export async function processQueue(): Promise<void> {
  const queue = await getQueue()
  if (queue.length === 0) return

  const isOnline = await checkDesktopStatus()
  if (!isOnline) return

  for (const item of queue) {
    try {
      await sendToDesktop(item.content)
      await removeFromQueue(item.id)
    } catch {
      item.attempts++
      if (item.attempts >= 5) {
        await removeFromQueue(item.id)
        // Notify user of permanent failure
      }
    }
  }
}

// Check periodically
chrome.alarms.create('processQueue', { periodInMinutes: 1 })
chrome.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === 'processQueue') {
    processQueue()
  }
})
```

## Popup UI

### Main Popup

```tsx
// src/popup/index.tsx
export default function Popup() {
  const [status, setStatus] = useState<'checking' | 'connected' | 'offline'>(
    'checking'
  )
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    checkDesktopStatus().then(online => {
      setStatus(online ? 'connected' : 'offline')
    })
  }, [])

  const handleSave = async () => {
    setSaving(true)
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })

    // Request capture from content script
    const content = await chrome.tabs.sendMessage(tab.id!, {
      action: 'capture',
    })

    const result = await sendToDesktop(content)
    setSaving(false)

    if (result.success) {
      // Show success, close popup
    } else if (result.queued) {
      // Show "saved for later" message
    }
  }

  return (
    <div className="w-80 p-4">
      <header className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold">Cortex</h1>
        <StatusIndicator status={status} />
      </header>

      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full py-2 bg-blue-600 text-white rounded"
      >
        {saving ? 'Saving...' : 'Save to Cortex'}
      </button>

      {status === 'offline' && (
        <p className="mt-2 text-sm text-gray-500">
          Desktop app not running. Content will be saved when you open Cortex.
        </p>
      )}
    </div>
  )
}
```

### Status Indicator

```tsx
function StatusIndicator({ status }: { status: string }) {
  const colors = {
    checking: 'bg-yellow-500',
    connected: 'bg-green-500',
    offline: 'bg-gray-400',
  }

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${colors[status]}`} />
      <span className="text-xs text-gray-500">
        {status === 'connected' ? 'Connected' : 'Offline'}
      </span>
    </div>
  )
}
```

## Keyboard Shortcuts

### Default Shortcuts

| Action         | Shortcut                       | Configurable |
| -------------- | ------------------------------ | ------------ |
| Save page      | `Ctrl+Shift+S` / `Cmd+Shift+S` | Yes          |
| Save selection | `Ctrl+Shift+H` / `Cmd+Shift+H` | Yes          |
| Open popup     | `Ctrl+Shift+C` / `Cmd+Shift+C` | Yes          |

### Implementation

```json
// manifest.json (generated by Plasmo)
{
  "commands": {
    "save-page": {
      "suggested_key": {
        "default": "Ctrl+Shift+S",
        "mac": "Command+Shift+S"
      },
      "description": "Save current page to Cortex"
    },
    "save-selection": {
      "suggested_key": {
        "default": "Ctrl+Shift+H",
        "mac": "Command+Shift+H"
      },
      "description": "Save selected text to Cortex"
    }
  }
}
```

```typescript
// src/background/index.ts
chrome.commands.onCommand.addListener(async command => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })

  switch (command) {
    case 'save-page':
      await chrome.tabs.sendMessage(tab.id!, { action: 'capture' })
      break
    case 'save-selection':
      await chrome.tabs.sendMessage(tab.id!, { action: 'captureSelection' })
      break
  }
})
```

## Content Extraction

### Site-Specific Handling

Some sites need special handling:

```typescript
// src/lib/extractor.ts
interface SiteExtractor {
  matches: (url: string) => boolean
  extract: (doc: Document) => ExtractedContent
}

const extractors: SiteExtractor[] = [
  {
    // Twitter/X
    matches: url => url.includes('twitter.com') || url.includes('x.com'),
    extract: doc => {
      const tweet = doc.querySelector('[data-testid="tweetText"]')
      return {
        content: tweet?.textContent || '',
        type: 'tweet',
      }
    },
  },
  {
    // YouTube
    matches: url => url.includes('youtube.com/watch'),
    extract: doc => {
      const title = doc.querySelector('h1.ytd-video-primary-info-renderer')
      const description = doc.querySelector('#description')
      return {
        content: description?.textContent || '',
        title: title?.textContent || '',
        type: 'video',
      }
    },
  },
  // Add more site-specific extractors
]

export function extractContent(url: string, doc: Document): ExtractedContent {
  // Try site-specific extractor first
  const extractor = extractors.find(e => e.matches(url))
  if (extractor) {
    return extractor.extract(doc)
  }

  // Fall back to Readability
  const reader = new Readability(doc.cloneNode(true) as Document)
  return reader.parse()
}
```

## Browser Support

### Manifest V3

Plasmo generates Manifest V3 compatible extension:

```typescript
// plasmo.config.ts
export default defineConfig({
  manifest: {
    permissions: ['activeTab', 'storage', 'alarms'],
    host_permissions: [
      'http://localhost:8742/*', // Desktop app communication
    ],
  },
})
```

### Cross-Browser

| Browser | Status    | Notes                   |
| ------- | --------- | ----------------------- |
| Chrome  | Primary   | Full support            |
| Firefox | Planned   | Manifest V3 differences |
| Safari  | Future    | Requires separate build |
| Edge    | Supported | Uses Chrome extension   |

## Testing

### Unit Tests

```typescript
// src/lib/__tests__/extractor.test.ts
import { extractContent } from '../extractor'

describe('Content Extraction', () => {
  it('extracts article content', () => {
    const doc = new DOMParser().parseFromString(
      `
      <html>
        <body>
          <article>
            <h1>Test Article</h1>
            <p>Article content here.</p>
          </article>
        </body>
      </html>
    `,
      'text/html'
    )

    const result = extractContent('https://example.com/article', doc)
    expect(result.title).toBe('Test Article')
    expect(result.textContent).toContain('Article content here')
  })
})
```

### E2E Tests

```typescript
// Using Playwright for extension testing
import { test, chromium } from '@playwright/test'

test('save page to Cortex', async () => {
  const pathToExtension = './dist/chrome-mv3'
  const context = await chromium.launchPersistentContext('', {
    headless: false,
    args: [
      `--disable-extensions-except=${pathToExtension}`,
      `--load-extension=${pathToExtension}`,
    ],
  })

  const page = await context.newPage()
  await page.goto('https://example.com')

  // Open extension popup
  // Click save button
  // Verify item created in desktop app
})
```

## Distribution

### Chrome Web Store

1. Build production bundle: `plasmo build --target=chrome-mv3`
2. Zip the `build/chrome-mv3-prod` directory
3. Upload to Chrome Web Store Developer Dashboard

### Firefox Add-ons

1. Build: `plasmo build --target=firefox-mv3`
2. Sign via Mozilla Add-ons

### Self-Distribution

For users who don't want to use stores:

1. Provide `.crx` file for Chrome
2. Instructions for loading unpacked extension

## Related Documentation

- [Product Roadmap](../product/roadmap.md) - Firefox/Safari extension plans
- [Python Backend API](../python-backend/architecture.md) - Desktop API endpoints
