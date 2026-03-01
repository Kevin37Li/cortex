# Task: Implement Search UI Components

## Summary

Build the search user interface: upgrade the existing search input with debouncing and clear functionality, create a results list showing ranked matches with relevance scores and snippets, click-through navigation to item detail, and proper empty/loading/error states. Add all translation keys for search UI strings.

## Acceptance Criteria

- [x] `src/components/search/SearchBar.tsx` created with: — `SearchBar.tsx:15`
  - Text input with search icon and placeholder text
  - Controlled API (`value` + `onValueChange`) so route-level state can drive both input and results
  - Auto-focuses when `searchFocused` becomes `true` in UI store (from Cmd+F)
  - Resets `searchFocused` to `false` after focusing (use `useRef` instead of `document.getElementById`)
  - Clear button when input has text
  - Accepts `className` prop, merged with `cn()`
  - Search type selector (hybrid/vector/fts) - optional, defaulted to hybrid in `SearchResults`
- [x] `src/components/search/SearchResults.tsx` created with: — `SearchResults.tsx:25`
  - Calls `useSearch()` with normalized query props (no raw `fetch()` in component)
  - Renders list of `SearchResultItem` results inside `ScrollArea`
  - Uses `ItemGroup` as list container for consistency with `ItemList`
  - Each result shows: item title, content type badge, chunk snippet (truncated), relevance score
  - Results are clickable and navigate to item detail view
  - Sorted by rank (already sorted by API)
  - Accepts `className` prop, merged with `cn()`
- [x] `src/components/search/SearchResultCard.tsx` created with: — `SearchResultCard.tsx:24`
  - Uses `Item`/`ItemContent`/`ItemTitle`/`ItemMedia` primitives from `@/components/ui/item` (matching `ItemCard` structure)
  - Content type indicator (icon or badge matching existing `items.contentType.*` translations)
  - Chunk content as snippet (first ~150 chars or highlight matching text) — `search-result-card.utils.ts:3`
  - Relevance score shown as visual indicator (bar, percentage, or dot) — `SearchResultCard.tsx:61-75`
  - Accepts `className` prop, merged with `cn()`
- [x] Empty states handled using `Empty`/`EmptyHeader`/`EmptyTitle`/`EmptyDescription` components: — `SearchResults.tsx:44-57, 110-126`
  - No query entered: prompt text ("Search your knowledge base")
  - Query entered, no results: "No results found" message with suggestion
  - Error state: error message with retry option — `SearchResults.tsx:87-108`
- [x] Loading state: skeleton or spinner while search is in progress — `SearchResults.tsx:60-85`
- [x] Debouncing implemented at route level (`src/routes/items/index.tsx`) with `useState` + `useEffect` (300ms) — `index.tsx:15-24`
- [x] Search bar integrated into items route layout (replacing `ItemsSearchInput`) — `index.tsx:34`
- [x] Click on result navigates to `/items/$id` using `<Link>` from TanStack Router — `SearchResultCard.tsx:38-40`
- [x] All UI strings use translation keys (no hardcoded strings)
- [x] Translation keys added to `locales/en.json` and `locales/zh.json` — verified with `jq` diff
- [x] All CSS uses logical properties (`ps-*`/`pe-*`, `start-*`/`end-*`, `text-start`/`text-end`) — `SearchBar.tsx:33,44,51`, `SearchResultCard.tsx:41,54`
- [x] State management follows documented patterns:
  - Search query state: `useState` in `src/routes/items/index.tsx` — `index.tsx:15`
  - Debounced query: `useState` + `useEffect` in `src/routes/items/index.tsx` — `index.tsx:16-24`
  - Search results: TanStack Query via `useSearch()` hook in `SearchResults` — `SearchResults.tsx:40`
  - Search focused: Zustand (UI store, set by Cmd+F command) — `SearchBar.tsx:18,27`
- [x] No Zustand destructuring anti-patterns — uses selector syntax throughout
- [x] No raw `fetch()` calls (uses `useSearch()` from services)
- [x] Avoid manual `useMemo`/`useCallback` unless needed (React Compiler handles memoization) — none used

## Dependencies

- Task 6: `useSearch()` TanStack Query hook
- Task 7: `searchFocused` UI store state, Cmd+F shortcut
- Phase 2: Item detail view (click-through target), content type badges, layout system
- Task 9: final repo-wide quality gate; this task should complete feature-level checks before Task 9

## Technical Notes

### Component Architecture

```
ItemsIndexPage (owns query + debouncedQuery + conditional rendering)
  ├── SearchBar (UI input + clear + focus behavior)
  └── SearchResults (data fetch + loading/empty/error/list rendering)
        └── SearchResultCard (single result row)
```

### Migration from ItemsSearchInput

The existing `ItemsSearchInput` component (`src/components/items/ItemsSearchInput.tsx`) provides basic search input with Cmd+F focus integration. `SearchBar` replaces it with controlled input behavior, clear button support, and route-level search wiring.

**Migration steps:**

1. Create `SearchBar` incorporating the existing focus behavior from `ItemsSearchInput`
2. Update `src/routes/items/index.tsx` to import `SearchBar` from `@/components/search`
3. Remove `src/components/items/ItemsSearchInput.tsx` and `src/components/items/ItemsSearchInput.test.tsx`
4. Update `src/components/items/index.ts` to remove `ItemsSearchInput` export
5. Migrate existing `items.search.placeholder` and `items.search.ariaLabel` keys to the `search.*` namespace

**Improvement over existing pattern:** Uses `useRef` for input focus instead of `document.getElementById`, which is cleaner and more React-idiomatic.

### SearchBar API

Keep `SearchBar` presentational for easier reuse/testing. It should not call `useSearch()` directly.

```typescript
interface SearchBarProps {
  value: string
  onValueChange: (value: string) => void
  className?: string
}
```

### Search Bar Integration

The search bar should be placed at the top of the content area, visible on the items route. Prefer route-level integration for MVP (search on items page only). The search bar replaces or sits above the item list when active.

### Debouncing Pattern

Use route-level state + effect for debouncing:

```typescript
function ItemsIndexPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  return (
    <>
      <SearchBar value={searchQuery} onValueChange={setSearchQuery} />
      {debouncedQuery.trim() ? (
        <SearchResults query={debouncedQuery} />
      ) : (
        <ItemList />
      )}
    </>
  )
}
```

### SearchResults Query State Pattern

`SearchResults` should own `useSearch()` and map query states to UI states:

- `isPending` for first-load skeleton/spinner
- `isError` for retry UI (`refetch()`)
- `isFetching` optional subtle refresh indicator while prior data remains visible
- Query disabled behavior comes from `useSearch()` (`enabled: Boolean(query.trim())`)

### Auto-Focus from Cmd+F

Subscribe to `searchFocused` from Zustand with selector syntax:

```typescript
const searchFocused = useUIStore(state => state.searchFocused)
const inputRef = useRef<HTMLInputElement>(null)

useEffect(() => {
  if (searchFocused && inputRef.current) {
    inputRef.current.focus()
    useUIStore.getState().setSearchFocused(false)
  }
}, [searchFocused])
```

### Result Card Design

Each result card should show:

- **Title line**: Item title (linked to detail) + content type icon
- **Snippet**: First ~150 chars of matching chunk content
- **Score**: Visual relevance indicator

Use existing UI primitives for consistency with `ItemCard`:

- `Item`/`ItemContent`/`ItemTitle`/`ItemMedia` from `@/components/ui/item` for card structure
- `Badge` from `@/components/ui/badge` for content type display
- `Empty`/`EmptyHeader`/`EmptyTitle`/`EmptyDescription` from `@/components/ui/empty` for empty/error states
- `ScrollArea` from `@/components/ui/scroll-area` for results list overflow

### Navigation

Use `<Link>` from TanStack Router for click-through (matching `ItemCard` pattern):

```typescript
import { Link } from '@tanstack/react-router'

function SearchResultCard({ result, className }: { result: SearchResultItem; className?: string }) {
  return (
    <ListItem variant="outline" size="sm" className={cn('gap-0 p-0', className)}>
      <Link
        to="/items/$id"
        params={{ id: result.item_id }}
        className="flex min-w-0 flex-1 items-center gap-3 rounded-lg px-3 py-2.5 text-start"
      >
        {/* ... */}
      </Link>
    </ListItem>
  )
}
```

**Note:** The route param is `id` (not `itemId`), matching `src/routes/items/$id.tsx`.

### Layout Integration

The search UI should integrate with the existing three-pane layout. When debounced query is non-empty, show search results in the content area. When cleared, show the regular item list.

Consider using a conditional render at the route level:

```typescript
function ItemsIndexPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  return (
    <div>
      <SearchBar value={searchQuery} onValueChange={setSearchQuery} />
      {debouncedQuery.trim() ? (
        <SearchResults query={debouncedQuery} />
      ) : (
        <ItemList />
      )}
    </div>
  )
}
```

### Translation Keys

Use `search.*` as a top-level namespace (search is a cross-cutting feature that will expand beyond items). Migrate existing `items.search.*` keys to `search.*`.

Add to both `locales/en.json` and `locales/zh.json`:

```json
{
  "search.placeholder": "Search your knowledge base...",
  "search.ariaLabel": "Search your knowledge base",
  "search.clear": "Clear search",
  "search.loading": "Searching...",
  "search.noResults": "No results found",
  "search.noResultsDescription": "Try different keywords or check your spelling",
  "search.error": "Search failed",
  "search.errorDescription": "Unable to search right now. Please try again.",
  "search.retry": "Retry",
  "search.resultCount_one": "{{count}} result",
  "search.resultCount_other": "{{count}} results",
  "search.relevance": "Relevance",
  "search.prompt": "Search your knowledge base",
  "search.promptDescription": "Find items using natural language or keywords"
}
```

**Note:** Pluralization uses `_one`/`_other` suffixes per documented i18next convention. Remove the old `items.search.placeholder` and `items.search.ariaLabel` keys after migration.

If search-type selector UI is implemented, also add:

- `search.type.hybrid`
- `search.type.vector`
- `search.type.fts`

### Accessibility

- Search input has `role="searchbox"` and `aria-label`
- Results list has `role="list"` with `role="listitem"` children
- Each `SearchResultCard` root row sets `role="listitem"` (or equivalent semantic element)
- Result cards are keyboard-navigable (Tab + Enter) via `<Link>` semantics
- Loading state announces via `aria-live="polite"`
- Score indicators have `aria-label` with percentage

### CSS Logical Properties

All new components must use CSS logical properties for RTL support:

- `ps-*`/`pe-*` not `pl-*`/`pr-*`
- `start-*`/`end-*` not `left-*`/`right-*`
- `text-start`/`text-end` not `text-left`/`text-right`
- `ms-*`/`me-*` not `ml-*`/`mr-*`

This matches the existing pattern in `ItemsSearchInput` (uses `start-2.5`, `ps-8`) and `ItemCard` (uses `text-start`, `pe-3`).

## Files to Create/Modify

**Create:**

- `src/components/search/SearchBar.tsx`
- `src/components/search/SearchResults.tsx`
- `src/components/search/SearchResultCard.tsx`
- `src/components/search/index.ts` (barrel export)
- `src/components/search/SearchBar.test.tsx`
- `src/components/search/SearchResults.test.tsx`
- `src/components/search/SearchResultCard.test.tsx`

**Modify:**

- `src/routes/items/index.tsx` - Replace `ItemsSearchInput` with `SearchBar`, add conditional search results rendering
- `src/components/items/index.ts` - Remove `ItemsSearchInput` export
- `locales/en.json` - Add `search.*` keys, remove `items.search.*` keys
- `locales/zh.json` - Add `search.*` keys, remove `items.search.*` keys

**Remove:**

- `src/components/items/ItemsSearchInput.tsx` - Replaced by `SearchBar`
- `src/components/items/ItemsSearchInput.test.tsx` - Tests replaced by `SearchBar.test.tsx`

### Testing Expectations

Use `src/test/test-utils.tsx` render helpers for component tests.

- `SearchBar.test.tsx`: renders input/icon/placeholder, clear button behavior, focus on `searchFocused=true`, resets flag after focus
- `SearchResults.test.tsx`: prompt state (empty query), loading (`isPending`), error + retry, no-results, populated list rendering
- `SearchResultCard.test.tsx`: `href` targets `/items/$id`, content type label, snippet truncation/line-clamp behavior, relevance indicator accessibility label

## Verification

```bash
# Task-level checks for this feature
bun run typecheck
bun run lint
bun run ast:lint
bun run format:check
bun run test:run

# Verify translations are complete
diff <(jq -S 'paths(scalars) | join(".")' locales/en.json) \
     <(jq -S 'paths(scalars) | join(".")' locales/zh.json)

# Full quality gate happens in Task 9
bun run check:all
```

---

## Implementation Details

_Tracked: 2026-03-01_

### Files Changed

| File                                                       | Change   | Description                                                                          |
| ---------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------ |
| `src/components/search/SearchBar.tsx`                      | Created  | Search input with icon, clear button, Cmd+F focus integration via useRef             |
| `src/components/search/SearchResults.tsx`                  | Created  | Results container with loading/error/empty/prompt states, uses `useSearch()`         |
| `src/components/search/SearchResultCard.tsx`               | Created  | Individual result card with title, content type badge, snippet, relevance bar        |
| `src/components/search/search-result-card.utils.ts`        | Created  | Pure helpers: `createSearchSnippet()`, `toRelevancePercent()`                        |
| `src/components/search/index.ts`                           | Created  | Barrel export for search components                                                  |
| `src/components/search/SearchBar.test.tsx`                 | Created  | Tests: controlled input, clear button, Cmd+F focus, searchFocused reset              |
| `src/components/search/SearchResults.test.tsx`             | Created  | Tests: prompt/loading/error/no-results/populated states                              |
| `src/components/search/SearchResultCard.test.tsx`          | Created  | Tests: metadata rendering, link href, snippet truncation, score clamping             |
| `src/components/search/SearchResults.integration.test.tsx` | Created  | Integration test for SearchResults                                                   |
| `src/lib/content-type.ts`                                  | Created  | Extracted `contentTypeConfig` mapping shared by `ItemCard` and `SearchResultCard`    |
| `src/routes/items/index.tsx`                               | Modified | Replaced `ItemsSearchInput` with `SearchBar`, added debounce + conditional rendering |
| `src/routes/items/index.test.tsx`                          | Created  | Tests: debounce timing, toggle between ItemList and SearchResults                    |
| `src/components/items/ItemCard.tsx`                        | Modified | Removed inline `contentTypeConfig`, imports from `@/lib/content-type`                |
| `src/components/items/index.ts`                            | Modified | Removed `ItemsSearchInput` export                                                    |
| `src/components/items/ItemsSearchInput.tsx`                | Deleted  | Replaced by `SearchBar`                                                              |
| `src/components/items/ItemsSearchInput.test.tsx`           | Deleted  | Replaced by `SearchBar.test.tsx`                                                     |
| `src/components/ui/input.tsx`                              | Modified | Added `ref` forwarding to `InputPrimitive`                                           |
| `locales/en.json`                                          | Modified | Added `search.*` keys, removed `items.search.*` keys                                 |
| `locales/zh.json`                                          | Modified | Added `search.*` keys (Chinese), removed `items.search.*` keys                       |

### Dependencies Added

- None (all UI primitives already in project)

### Metrics

- **887 lines** of new code across 11 new files
- **19 files** changed total (11 created, 6 modified, 2 deleted)
- **363 tests** passing (all Python + JS)
- `bun run check:all` passes cleanly
- Translation keys verified: en.json and zh.json in sync

---

## Learning Report

_Generated: 2026-03-01_

### Summary

Built the search UI layer for Cortex: a controlled `SearchBar` with debouncing and Cmd+F focus, a `SearchResults` container that maps TanStack Query states to loading/error/empty/results UI, and a `SearchResultCard` that displays item metadata with a relevance bar. The search bar replaces the old `ItemsSearchInput` and integrates at the route level with conditional rendering between search results and the item list.

### Patterns & Decisions

- **Controlled input at route level**: `SearchBar` is purely presentational (`value` + `onValueChange`). The `ItemsIndexPage` owns the query state and debounce logic, keeping data flow unidirectional and testable.
- **Selector-based Zustand access**: `useUIStore(state => state.searchFocused)` with `getState()` for writes — no destructuring, matching the documented performance pattern.
- **Extracted `contentTypeConfig`**: The content type icon/label mapping was duplicated between `ItemCard` and `SearchResultCard`. Extracted to `src/lib/content-type.ts` for single source of truth.
- **Pure utility extraction**: `createSearchSnippet()` and `toRelevancePercent()` are pure functions in a separate `.utils.ts` file, making them trivially testable without component rendering.
- **Input ref forwarding fix**: The `Input` component (shadcn/base-ui) wasn't forwarding `ref` to the underlying `InputPrimitive`. Fixed by explicitly passing `ref` through, enabling `useRef`-based focus in `SearchBar`.
- **Translation namespace migration**: Moved from `items.search.*` to `search.*` top-level namespace since search is cross-cutting. Used i18next `_one`/`_other` convention for pluralization.

### Challenges & Solutions

- **Ref forwarding gap**: The `Input` component didn't forward refs to the DOM element, causing `inputRef.current.focus()` to fail silently. Solved by adding explicit `ref` prop passthrough in `input.tsx`.
- **Test isolation for route component**: Testing `ItemsIndexPage` required mocking both `@/components/items` and `@/components/search` to avoid deep dependency trees. Used `vi.mock()` with inline mock components and dynamic import (`await import('./index')`) to ensure mock ordering.
- **Debounce timing tests**: Used `vi.useFakeTimers()` with precise `advanceTimersByTime(299)` and `advanceTimersByTime(1)` to verify the 300ms debounce boundary behavior.

### Lessons Learned

- **What worked well**: The controlled input + route-level debounce pattern from the task spec was clean to implement and test. Extracting pure utilities made testing easy — no mocking needed.
- **What could be improved**: The `Input` component's ref forwarding issue could have been caught earlier with a ref-forwarding test in the UI component library.
- **Recommendation**: When building new components that wrap `<input>`, always verify ref forwarding works before building features that depend on programmatic focus.

### Documentation Impact

- `src/lib/content-type.ts` establishes a pattern for shared content type configuration. If more content types are added, update this file.
- The route-level debounce pattern (`useState` + `useEffect` + `setTimeout`) could be documented as a recommended approach in state management docs.
- The `search.*` translation namespace is now the canonical location for search-related strings.
