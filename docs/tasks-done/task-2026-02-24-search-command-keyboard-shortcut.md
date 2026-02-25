# Task: Register Search Command and Keyboard Shortcut

## Summary

Register a `focus-search` command in the command system with `Cmd+F` keyboard shortcut. Add a `searchFocused` state flag to the UI store so the search input component (Task 8) can respond to the shortcut. Add translation keys for the search command.

## Acceptance Criteria

- [x] `src/lib/commands/search-commands.ts` created with `searchCommands` array
- [x] `src/lib/commands/search-commands.test.ts` created (metadata + execute behavior)
- [x] `focus-search` command registered with:
  - `id: 'focus-search'`
  - `labelKey: 'commands.focusSearch.label'`
  - `descriptionKey: 'commands.focusSearch.description'`
  - `icon: Search` (from lucide-react)
  - `group: 'navigation'`
  - `shortcut: '⌘+F'`
  - `keywords: ['search', 'find', 'query']`
- [x] Command `execute` sets `searchFocused: true` in UI store via `getState()`
- [x] UI store updated with `searchFocused: boolean` state and `setSearchFocused(focused: boolean)` action
- [x] `searchCommands` registered in `src/lib/commands/index.ts`
- [x] `Cmd+F` shortcut handled in `src/hooks/use-keyboard-shortcuts.ts` (prevents default browser find)
- [x] `Cmd+F` suppressed when dialogs are open (command palette, preferences, quick note)
- [x] Translation keys added to `locales/en.json` and `locales/zh.json`:
  - `commands.focusSearch.label`
  - `commands.focusSearch.description`
- [x] Tests added to `src/hooks/use-keyboard-shortcuts.test.ts` for Cmd+F behavior
- [x] Tests added to `src/store/ui-store.test.ts` for `searchFocused` state
- [x] Tests added to `src/lib/commands/search-commands.test.ts`:
  - metadata matches command conventions
  - `execute` sets `searchFocused` to `true`
- [x] JSDoc updated in `use-keyboard-shortcuts.ts` and `useMainWindowEventListeners.ts`
- [x] `docs/developer/core-systems/keyboard-shortcuts.md` updated with Cmd+F in:
  - Current Shortcuts table
  - Architecture example snippet and/or shortcut list bullets
- [x] `bun run check:all` passes

## Dependencies

- `docs/tasks-done/task-2026-02-22-tanstack-query-search-hooks.md` (Task 6 complete)
- This task must complete before Task 8 (`docs/tasks-todo/task-8-search-results-ui.md`) so Cmd/Ctrl+F focus wiring exists
- Command system (`src/lib/commands/`), UI store (`src/store/ui-store.ts`), keyboard shortcuts hook, locale keys

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
    set({ searchFocused: focused }, undefined, 'setSearchFocused'),
}))
```

**Note**: Use `undefined` (not `false`) as the second argument to `set()` — this matches the established pattern throughout the UI store.

The search input component (Task 8) will subscribe to `searchFocused` and auto-focus when it becomes `true`, then set it back to `false` after focusing.

### Group Key

Use `group: 'navigation'` for this command to match existing command groups in locale files. Do not introduce `commands.group.search` in this task.

### Keyboard Shortcut

In `src/hooks/use-keyboard-shortcuts.ts`, add handling for `Cmd+F` with the dialog guard that existing shortcuts use:

```typescript
case 'f': {
  e.preventDefault()  // Prevent browser find dialog
  if (commandPaletteOpen || preferencesOpen || quickNoteDialogOpen) {
    break
  }
  const { setSearchFocused } = useUIStore.getState()
  setSearchFocused(true)
  break
}
```

**Important**: Use `getState()` in the event handler, not a hook subscription, to avoid stale closures. The `commandPaletteOpen`, `preferencesOpen`, and `quickNoteDialogOpen` values are already read via `getState()` at the top of the handler.

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
  "commands.focusSearch.label": "搜索",
  "commands.focusSearch.description": "搜索你的知识库"
}
```

### Tests

#### Keyboard Shortcut Tests (`src/hooks/use-keyboard-shortcuts.test.ts`)

Add tests for:

- `Cmd+F` sets `searchFocused` to `true`
- `Ctrl+F` sets `searchFocused` to `true` (cross-platform)
- `Cmd+F` is suppressed when command palette is open
- `Cmd+F` is suppressed when preferences dialog is open
- `Cmd+F` is suppressed when quick note dialog is open

Update `beforeEach` state reset to include `searchFocused: false`.

#### UI Store Tests (`src/store/ui-store.test.ts`)

Add tests for:

- `searchFocused` initial value is `false`
- `setSearchFocused(true)` sets state to `true`
- `setSearchFocused(false)` resets state to `false`

#### Search Command Tests (`src/lib/commands/search-commands.test.ts`)

Follow the same pattern as `note-commands.test.ts` / `import-commands.test.ts`:

- metadata assertions (`id`, `labelKey`, `descriptionKey`, `group`, `shortcut`, `keywords`)
- execute assertion verifies `useUIStore.getState().searchFocused` becomes `true`

### Documentation Updates

#### JSDoc in `src/hooks/use-keyboard-shortcuts.ts`

Add `- Cmd/Ctrl+F : Focus search` to the shortcut list in the JSDoc comment.

#### JSDoc in `src/hooks/useMainWindowEventListeners.ts`

Add `Cmd+F` to the shortcut list in the JSDoc comment.

#### Keyboard Shortcuts Doc (`docs/developer/core-systems/keyboard-shortcuts.md`)

Add row to the Current Shortcuts table:

| Focus Search | Cmd+F | Ctrl+F | Focuses the search input |

### ast-grep Rule

The UI store is already covered by the no-destructure rule in `.ast-grep/rules/zustand/no-destructure.yml` (it matches `useUIStore`). No update needed. Verify by running `bun run ast:lint`.

### Note on `keywords` Field

The `keywords` array is defined per the `AppCommand` type but the command registry's `getAllCommands` search currently only checks `labelKey` and `descriptionKey` translations — it does not search `keywords`. The keywords are included here for correctness per the type definition and will become functional when the registry search is updated.

## Files to Create/Modify

**Create:**

- `src/lib/commands/search-commands.ts`
- `src/lib/commands/search-commands.test.ts`

**Modify:**

- `src/lib/commands/index.ts` - Register search commands
- `src/store/ui-store.ts` - Add `searchFocused` state
- `src/store/ui-store.test.ts` - Add tests for `searchFocused`
- `src/hooks/use-keyboard-shortcuts.ts` - Add Cmd+F handler with dialog guard, update JSDoc
- `src/hooks/use-keyboard-shortcuts.test.ts` - Add Cmd+F tests
- `src/hooks/useMainWindowEventListeners.ts` - Update JSDoc shortcut list
- `locales/en.json` - Add search command translation keys
- `locales/zh.json` - Add search command translation keys
- `docs/developer/core-systems/keyboard-shortcuts.md` - Add Cmd+F to shortcuts table

## Verification

```bash
bun run test:run src/lib/commands/search-commands.test.ts src/hooks/use-keyboard-shortcuts.test.ts src/store/ui-store.test.ts
bun run check:all
```

---

## Implementation Details

_Tracked: 2026-02-25_

### Files Changed

| File                                                | Change   | Description                                                                                                                                            |
| --------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/lib/commands/search-commands.ts`               | Created  | Added `focus-search` command metadata (`⌘+F`, navigation group, keywords) and `execute` handler that sets `searchFocused` via `useUIStore.getState()`. |
| `src/lib/commands/search-commands.test.ts`          | Created  | Added metadata and execute-behavior coverage for the new `focus-search` command.                                                                       |
| `src/lib/commands/index.ts`                         | Modified | Registered `searchCommands` during command system initialization and exported it from the module barrel.                                               |
| `src/lib/commands/registry.ts`                      | Modified | Extended command filtering to include `keywords` matching and label/description fallback when no translator function is provided.                      |
| `src/lib/commands/commands.test.ts`                 | Modified | Added coverage for keyword filtering and system-level registration of `focus-search`; updated store mocks for new UI store fields/actions.             |
| `src/store/ui-store.ts`                             | Modified | Added `searchFocused` state and `setSearchFocused(focused)` action using the existing Zustand action pattern.                                          |
| `src/store/ui-store.test.ts`                        | Modified | Added tests for `searchFocused` default state and setter behavior (`true`/`false`).                                                                    |
| `src/hooks/use-keyboard-shortcuts.ts`               | Modified | Added `Cmd/Ctrl+F` shortcut handling that prevents browser find and respects dialog guards (command palette/preferences/quick note).                   |
| `src/hooks/use-keyboard-shortcuts.test.ts`          | Modified | Added `Cmd+F`/`Ctrl+F` behavior tests, including dialog suppression cases.                                                                             |
| `src/hooks/useMainWindowEventListeners.ts`          | Modified | Updated shortcut JSDoc list to include `Cmd+F`.                                                                                                        |
| `locales/en.json`                                   | Modified | Added `commands.focusSearch.label` and `commands.focusSearch.description` translation entries.                                                         |
| `locales/zh.json`                                   | Modified | Added `commands.focusSearch.label` and `commands.focusSearch.description` translation entries.                                                         |
| `docs/developer/core-systems/keyboard-shortcuts.md` | Modified | Added Focus Search row to the shortcuts table and updated keyboard architecture examples/listings.                                                     |

### Dependencies Added

- None

---

## Learning Report

_Generated: 2026-02-25_

### Summary

Implemented end-to-end command-level keyboard support for search focus: command registration, global shortcut handling, UI store signaling, i18n keys, tests, and developer docs updates.

### Patterns and Decisions

- Followed command-system architecture by introducing a dedicated `searchCommands` module and registering it centrally.
- Kept keyboard handlers state-safe by using `useUIStore.getState()` in event callbacks.
- Preserved existing modal safety pattern by suppressing focus behavior when command palette, preferences, or quick note dialogs are open.
- Maintained localization conventions with new command translation keys in both supported locales.

### Challenges and Solutions

- Challenge: `keywords` existed in command definitions but were not used in filtering.
  - Solution: Extended `getAllCommands` to include keyword matching, and added tests to lock behavior.
- Challenge: Ensuring shortcut behavior remains deterministic while dialogs are open.
  - Solution: Added explicit guard-coverage tests for each dialog state.

### Lessons Learned

- Command metadata (`keywords`) should be exercised by registry logic to avoid drift between type contracts and runtime behavior.
- UI store boolean trigger flags are effective for cross-component focus handoff when paired with immediate reset semantics in consumers.
- Including shortcut docs and JSDoc updates in the same change helps keep developer-facing behavior discoverable and aligned with implementation.
