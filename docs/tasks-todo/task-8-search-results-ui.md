# Task: Implement Search UI Components

## Summary

Build the search user interface: a search input bar with debouncing, a results list showing ranked matches with relevance scores and snippets, click-through navigation to item detail, and proper empty/loading/error states. Add all translation keys for search UI strings.

## Acceptance Criteria

- [ ] `src/components/search/SearchBar.tsx` created with:
  - Text input with search icon and placeholder text
  - Debounced input (300ms) before triggering search
  - Auto-focuses when `searchFocused` becomes `true` in UI store (from Cmd+F)
  - Resets `searchFocused` to `false` after focusing
  - Clear button when input has text
  - Search type selector (hybrid/vector/fts) - optional, can default to hybrid
- [ ] `src/components/search/SearchResults.tsx` created with:
  - Renders list of `SearchResultItem` results
  - Each result shows: item title, content type badge, chunk snippet (truncated), relevance score
  - Results are clickable and navigate to item detail view
  - Sorted by rank (already sorted by API)
- [ ] `src/components/search/SearchResultCard.tsx` created with:
  - Item title as primary text
  - Content type indicator (icon or badge matching existing `items.contentType.*` translations)
  - Chunk content as snippet (first ~150 chars or highlight matching text)
  - Relevance score shown as visual indicator (bar, percentage, or dot)
- [ ] Empty states handled:
  - No query entered: prompt text ("Search your knowledge base")
  - Query entered, no results: "No results found" message with suggestion
  - Error state: error message with retry option
- [ ] Loading state: skeleton or spinner while search is in progress
- [ ] Search bar integrated into main content area layout (above item list)
- [ ] Click on result navigates to `/items/:id` using TanStack Router
- [ ] All UI strings use translation keys (no hardcoded strings)
- [ ] Translation keys added to `locales/en.json` and `locales/zh.json`
- [ ] State management follows documented patterns:
  - Search query state: `useState` (component-local)
  - Debounced query: `useState` (component-local)
  - Search results: TanStack Query via `useSearch()` hook
  - Search focused: Zustand (UI store, set by Cmd+F command)
- [ ] No Zustand destructuring anti-patterns
- [ ] No raw `fetch()` calls (uses `useSearch()` from services)

## Dependencies

- Task 6: `useSearch()` TanStack Query hook
- Task 7: `searchFocused` UI store state, Cmd+F shortcut
- Phase 2: Item detail view (click-through target), content type badges, layout system

## Technical Notes

### Component Architecture

```
SearchBar (manages input, debounce, focus)
  └── SearchResults (renders results or states)
        └── SearchResultCard (single result)
```

### Search Bar Integration

The search bar should be placed at the top of the content area, visible on the items route. Two approaches:

1. **Route-level**: Add search to the items route layout
2. **Layout-level**: Add search to the main content layout (always visible)

Prefer approach 1 for MVP (search on items page only). The search bar replaces or sits above the item list when active.

### Debouncing Pattern

Use a local state + effect pattern for debouncing:

```typescript
function SearchBar() {
  const [inputValue, setInputValue] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(inputValue)
    }, 300)
    return () => clearTimeout(timer)
  }, [inputValue])

  const { data, isLoading, isError, error } = useSearch({
    query: debouncedQuery,
  })

  // ...
}
```

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

Use existing shadcn/ui components (Card, Badge) for consistent styling.

### Navigation

Use TanStack Router for click-through:

```typescript
import { useNavigate } from '@tanstack/react-router'

function SearchResultCard({ result }: { result: SearchResultItem }) {
  const navigate = useNavigate()

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => navigate({ to: '/items/$itemId', params: { itemId: result.item_id } })}
    >
      {/* ... */}
    </div>
  )
}
```

### Layout Integration

The search UI should integrate with the existing three-pane layout. When search is active (has query), show search results in the content area. When search is cleared, show the regular item list.

Consider using a conditional render at the route level:

```typescript
function ItemsPage() {
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <div>
      <SearchBar value={searchQuery} onChange={setSearchQuery} />
      {searchQuery.trim() ? (
        <SearchResults query={searchQuery} />
      ) : (
        <ItemList />
      )}
    </div>
  )
}
```

### Translation Keys

Add to both `locales/en.json` and `locales/zh.json`:

```json
{
  "search.placeholder": "Search your knowledge base...",
  "search.clear": "Clear search",
  "search.loading": "Searching...",
  "search.noResults": "No results found",
  "search.noResultsDescription": "Try different keywords or check your spelling",
  "search.error": "Search failed",
  "search.errorDescription": "Unable to search right now. Please try again.",
  "search.retry": "Retry",
  "search.resultCount": "{{count}} result",
  "search.resultCount_other": "{{count}} results",
  "search.relevance": "Relevance",
  "search.prompt": "Search your knowledge base",
  "search.promptDescription": "Find items using natural language or keywords"
}
```

### Accessibility

- Search input has `role="searchbox"` and `aria-label`
- Results list has `role="list"` with `role="listitem"` children
- Result cards are keyboard-navigable (Tab + Enter)
- Loading state announces via `aria-live="polite"`
- Score indicators have `aria-label` with percentage

## Files to Create/Modify

**Create:**

- `src/components/search/SearchBar.tsx`
- `src/components/search/SearchResults.tsx`
- `src/components/search/SearchResultCard.tsx`

**Modify:**

- `src/routes/` - Integrate search into items route layout
- `locales/en.json` - Add search UI translation keys
- `locales/zh.json` - Add search UI translation keys (Chinese)

## Verification

```bash
bun run typecheck
bun run lint
bun run ast:lint
bun run format:check
bun run test:run

# Verify translations are complete
diff <(jq -S 'paths(scalars) | join(".")' locales/en.json) \
     <(jq -S 'paths(scalars) | join(".")' locales/zh.json)
```
