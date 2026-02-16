# Task: Register Search Command and Keyboard Shortcut

## Summary

Register a `focus-search` command in the command system with `Cmd+F` keyboard shortcut. Add a `searchFocused` state flag to the UI store so the search input component (Task 8) can respond to the shortcut. Add translation keys for the search command.

## Acceptance Criteria

- [ ] `src/lib/commands/search-commands.ts` created with `searchCommands` array
- [ ] `focus-search` command registered with:
  - `id: 'focus-search'`
  - `labelKey: 'commands.focusSearch.label'`
  - `descriptionKey: 'commands.focusSearch.description'`
  - `icon: Search` (from lucide-react)
  - `group: 'navigation'`
  - `shortcut: '⌘+F'`
  - `keywords: ['search', 'find', 'query']`
- [ ] Command `execute` sets `searchFocused: true` in UI store via `getState()`
- [ ] UI store updated with `searchFocused: boolean` state and `setSearchFocused(focused: boolean)` action
- [ ] `searchCommands` registered in `src/lib/commands/index.ts`
- [ ] `Cmd+F` shortcut handled in `src/hooks/use-keyboard-shortcuts.ts` (prevents default browser find)
- [ ] Translation keys added to `locales/en.json` and `locales/zh.json`:
  - `commands.focusSearch.label`
  - `commands.focusSearch.description`
  - `commands.group.search` (if using a new group)
- [ ] `.ast-grep/rules/zustand/no-destructure.yml` updated if needed (UI store already covered)
- [ ] `bun run ast:lint` passes (no destructuring anti-patterns)

## Dependencies

- Phase 1: Command system (`src/lib/commands/`), UI store (`src/store/ui-store.ts`), keyboard shortcuts hook
- Phase 1: Translation keys pattern in `locales/`

## Technical Notes

### Search Command File

```typescript
// src/lib/commands/search-commands.ts
import { Search } from 'lucide-react'
import type { AppCommand } from './types'
import { useUIStore } from '@/store/ui-store'

export const searchCommands: AppCommand[] = [
  {
    id: 'focus-search',
    labelKey: 'commands.focusSearch.label',
    descriptionKey: 'commands.focusSearch.description',
    icon: Search,
    group: 'navigation',
    shortcut: '⌘+F',
    keywords: ['search', 'find', 'query'],

    execute: () => {
      const { setSearchFocused } = useUIStore.getState()
      setSearchFocused(true)
    },

    isAvailable: () => true,
  },
]
```

### UI Store Update

Add to `src/store/ui-store.ts`:

```typescript
interface UIState {
  // ... existing state
  searchFocused: boolean
  setSearchFocused: (focused: boolean) => void
}

export const useUIStore = create<UIState>()(set => ({
  // ... existing state
  searchFocused: false,
  setSearchFocused: focused =>
    set({ searchFocused: focused }, false, 'setSearchFocused'),
}))
```

The search input component (Task 8) will subscribe to `searchFocused` and auto-focus when it becomes `true`, then set it back to `false` after focusing.

### Keyboard Shortcut

In `src/hooks/use-keyboard-shortcuts.ts`, add handling for `Cmd+F`:

```typescript
case 'f': {
  e.preventDefault()  // Prevent browser find dialog
  const { setSearchFocused } = useUIStore.getState()
  setSearchFocused(true)
  break
}
```

**Important**: Use `getState()` in the event handler, not a hook subscription, to avoid stale closures.

### Command Registration

In `src/lib/commands/index.ts`:

```typescript
import { searchCommands } from './search-commands'

export function initializeCommandSystem(): void {
  // ... existing registrations
  registerCommands(searchCommands)
}

export { searchCommands }
```

### Translation Keys

```json
// locales/en.json
{
  "commands.focusSearch.label": "Search",
  "commands.focusSearch.description": "Search your knowledge base"
}

// locales/zh.json
{
  "commands.focusSearch.label": "??????",
  "commands.focusSearch.description": "??????????????????"
}
```

### ast-grep Rule

The UI store is already covered by the no-destructure rule in `.ast-grep/rules/zustand/no-destructure.yml` (it matches `useUIStore`). No update needed unless the rule pattern is narrower than expected. Verify by running `bun run ast:lint`.

## Files to Create/Modify

**Create:**

- `src/lib/commands/search-commands.ts`

**Modify:**

- `src/lib/commands/index.ts` - Register search commands
- `src/store/ui-store.ts` - Add `searchFocused` state
- `src/hooks/use-keyboard-shortcuts.ts` - Add Cmd+F handler
- `locales/en.json` - Add search command translation keys
- `locales/zh.json` - Add search command translation keys

## Verification

```bash
bun run typecheck
bun run lint
bun run ast:lint
bun run test:run
```
