# State Management

Four-layer architecture for state management, with clear ownership boundaries.

## State Ownership

| State Type       | Owner           | Example                     |
| ---------------- | --------------- | --------------------------- |
| URL/route params | TanStack Router | Current route, item ID      |
| Component UI     | useState        | Dropdown open, form input   |
| Global UI        | Zustand         | Sidebar visible, modal open |
| Server data      | TanStack Query  | Items list, conversations   |

## The Three Layers (UI State)

```
┌─────────────────────────────────────┐
│           useState                  │  ← Component UI State
│  ┌─────────────────────────────────┐│
│  │          Zustand                ││  ← Global UI State
│  │  ┌─────────────────────────────┐││
│  │  │      TanStack Query         │││  ← Persistent Data
│  │  └─────────────────────────────┘││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

TanStack Router sits alongside this model, owning URL-derived state separately.

### Layer 1: TanStack Query (Persistent Data)

Use for data that:

- Comes from Tauri backend (file system, external APIs)
- Benefits from caching and automatic refetching
- Has loading, error, and success states

```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ['user', userId],
  queryFn: () => commands.getUser({ userId }),
  enabled: !!userId,
})
```

See [error-handling.md](./error-handling.md) for retry configuration and error display patterns.

### Layer 2: Zustand (Global UI State)

Use for transient global state:

- Panel visibility, layout state
- Command palette open/closed
- UI modes and navigation

```typescript
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

interface UIState {
  sidebarVisible: boolean
  toggleSidebar: () => void
}

export const useUIStore = create<UIState>()(
  devtools(
    set => ({
      sidebarVisible: true,
      toggleSidebar: () =>
        set(state => ({ sidebarVisible: !state.sidebarVisible })),
    }),
    { name: 'ui-store' }
  )
)
```

### Layer 3: useState (Component State)

Use for state that:

- Only affects UI presentation
- Is derived from props or global state
- Is tightly coupled to component lifecycle

```typescript
const [isDropdownOpen, setIsDropdownOpen] = useState(false)
const [windowWidth, setWindowWidth] = useState(window.innerWidth)
```

## Performance Patterns (Critical)

### The `getState()` Pattern

**Problem**: Subscribing to store data in callbacks causes render cascades.

**Solution**: Use `getState()` for callbacks that need current state.

```typescript
// ❌ BAD: Causes render cascade on every store change
const { currentFile, isDirty, saveFile } = useEditorStore()

const handleSave = useCallback(() => {
  if (currentFile && isDirty) {
    void saveFile()
  }
}, [currentFile, isDirty, saveFile]) // Re-creates on every change!

// ✅ GOOD: No cascade, stable callback
const handleSave = useCallback(() => {
  const { currentFile, isDirty, saveFile } = useEditorStore.getState()
  if (currentFile && isDirty) {
    void saveFile()
  }
}, []) // Stable dependency array
```

**When to use `getState()`:**

- In `useCallback` dependencies when you need current state but don't want re-renders
- In event handlers for accessing latest state without subscriptions
- In `useEffect` with empty deps when you need current state on mount only
- In async operations when state might change during execution

### Store Subscription Optimization

```typescript
// ❌ BAD: Object destructuring subscribes to entire store
const { currentFile } = useEditorStore()

// ✅ GOOD: Selector only re-renders when this specific value changes
const currentFile = useEditorStore(state => state.currentFile)

// ✅ GOOD: Derived selector for minimal re-renders
const hasCurrentFile = useEditorStore(state => !!state.currentFile)
const currentFileName = useEditorStore(state => state.currentFile?.name)
```

### CSS Visibility vs Conditional Rendering

For stateful UI components (like `react-resizable-panels`), use CSS visibility:

```typescript
// ❌ BAD: Conditional rendering breaks stateful components
{sidebarVisible ? <ResizablePanel /> : null}

// ✅ GOOD: CSS visibility preserves component tree
<ResizablePanel className={sidebarVisible ? '' : 'hidden'} />
```

### React Compiler (Automatic Memoization)

This app uses React Compiler which automatically handles memoization. You do **not** need to manually add:

- `useMemo` for computed values
- `useCallback` for function references
- `React.memo` for components

**Note:** The `getState()` pattern is still critical - it avoids store subscriptions, not memoization.

## Store Boundaries

**UIStore** - Use for:

- Panel visibility
- Layout state
- Command palette state
- UI modes and navigation

**Feature-specific stores** - Use for:

- Domain-specific state (e.g., `useDocumentStore`)
- Feature flags and configuration
- Temporary workflow state

## Adding a New Store

1. Create store file in `src/store/`
2. Follow the pattern with `devtools` middleware
3. Add no-destructure rule to `.ast-grep/rules/zustand/no-destructure.yml`

```yaml
rule:
  any:
    - pattern: const { $$$PROPS } = useUIStore($$$ARGS)
    - pattern: const { $$$PROPS } = useNewStore($$$ARGS) # Add new store
```

## Routing State

TanStack Router owns URL-derived state. Use hash history for Tauri compatibility:

```typescript
// src/lib/router.ts
import { createRouter, createHashHistory } from '@tanstack/react-router'

const hashHistory = createHashHistory()
export const router = createRouter({ routeTree, history: hashHistory })
```

**Why hash history?** Tauri uses `file://` protocol where browser history API doesn't work. Hash-based URLs (`/#/items`) work correctly with local file protocols.

### Route File Structure

File-based routing with folder organization:

```
src/routes/
├── __root.tsx           # Root layout (wraps all routes)
├── index.tsx            # / (redirect to /items)
├── $.tsx                # Catch-all 404
├── items/
│   ├── route.tsx        # /items layout (contains Outlet)
│   ├── index.tsx        # /items list view
│   └── $id.tsx          # /items/:id detail view
├── conversations/
│   ├── route.tsx        # /conversations layout
│   ├── index.tsx        # /conversations list view
│   └── $id.tsx          # /conversations/:id detail view
└── settings/
    └── route.tsx        # /settings
```

**Naming conventions:**

- `route.tsx` - Layout wrapper containing `<Outlet />`
- `index.tsx` - Index route content
- `$param.tsx` - Dynamic parameter route

### Accessing Route State

```typescript
// ✅ GOOD: Type-safe params from route module
import { Route } from './items/$id'
const { id } = Route.useParams()

// ✅ GOOD: Navigation in non-React code
import { router } from '@/lib/router'
router.navigate({ to: '/items' })
```
