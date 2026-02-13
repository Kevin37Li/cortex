# Task: Implement Quick Note Creation UI

## Summary

Build the quick note creation interface that allows users to write and save text notes from the desktop app. Includes a simple form with title and content fields, Markdown support in content, and immediate save to the backend. Uses TanStack Form (`@tanstack/react-form`) for component-local form state and validation, Zustand for dialog visibility (so commands/shortcuts/sidebar can open it), and TanStack Query mutation for submission.

## Acceptance Criteria

- [x] Quick note creation accessible from all three entry points: sidebar button, command palette command, and `Cmd/Ctrl+N` shortcut - Implemented in `LeftSideBar.tsx:43-49`, `note-commands.ts:5-18`, `use-keyboard-shortcuts.ts:29-34`
- [x] Quick note dialog is mounted globally in `MainWindowShell` so it can be opened from any route - Implemented in `MainWindowShell.tsx:85`
- [x] Note creation form with: title input (required), content textarea (required, Markdown supported) - Implemented in `QuickNoteDialog.tsx:89-158`
- [x] Content type automatically set to `'note'` - Implemented in `QuickNoteDialog.tsx:49`
- [x] Submit button saves note via `useCreateItem()` mutation - Implemented in `QuickNoteDialog.tsx:47-48`
- [x] Success: dialog closes, form resets, success toast shown via `notifications.success()`, item list refreshed - Implemented in `QuickNoteDialog.tsx:53-55`
- [x] Error: error message displayed via `notifications.error()`, form preserved for retry - Implemented in `QuickNoteDialog.tsx:56-58`
- [x] Loading state: submit button disabled with spinner icon and saving label during save - Implemented in `QuickNoteDialog.tsx:160-186`
- [x] Keyboard shortcut: `Cmd/Ctrl+N` opens quick note from `useKeyboardShortcuts` - Implemented in `use-keyboard-shortcuts.ts:28-34`
- [x] Dialog open/close state managed via Zustand UIStore (`quickNoteDialogOpen`) - Implemented in `ui-store.ts:9,83-91`
- [x] Form state managed by TanStack Form (`useForm` + `form.Field`) with built-in validation for both title and content - Implemented in `QuickNoteDialog.tsx:43-60,89-158`
- [x] Dialog component reads UIStore state with selector syntax (no destructuring) - Implemented in `QuickNoteDialog.tsx:37-40`
- [x] All user-facing strings use i18n translation keys - Implemented in `locales/en.json`, `locales/zh.json`

## Dependencies

- Task 12: TanStack Query service hooks (`useCreateItem()`)
- Task 13: Item list (to verify created items appear)
- Phase 1: Sidebar layout, command system, i18n, toast notifications (`sonner`)
- **New dependency**: Install `@tanstack/react-form` — `bun add @tanstack/react-form`
- TanStack Form rationale: forward-compatibility for richer capture forms (more fields, cross-field validation, reusable form patterns)

## Technical Notes

- TanStack Form (`@tanstack/react-form`) is used as a helper for component-local form state (aligned with Layer 3 ownership, not a new global state layer)
- Per state management decision tree: dialog open/close uses Zustand (needed across components — command system triggers it)
- Per state management decision tree: submission uses TanStack Query (persistent data) — TanStack Form's `onSubmit` calls the `useCreateItem()` mutation
- Add a shared `openQuickNoteDialog()` helper to avoid drift across sidebar/shortcut/command entry points
- The sidebar already has placeholder navigation — add a "New Note" button wired to the shared open helper
- Use shadcn/ui components: `Dialog`, `Input`, `Textarea`, `Button`
- Per `docs/developer/core-systems/command-system.md`: register keyboard shortcut with `labelKey`
- The quick note is a dialog (modal) — simpler for MVP
- Markdown rendering is not needed at creation time — just a plain textarea that accepts Markdown
- Use `notifications.success()` / `notifications.error()` from `@/lib/notifications` for toasts (not raw Sonner)
- Use selector syntax when reading UIStore: `const open = useUIStore(state => state.quickNoteDialogOpen)` — destructuring triggers ast-grep rule
- Mount `<QuickNoteDialog />` in `MainWindowShell` with other global overlays (`CommandPalette`, `PreferencesDialog`)

## Component Structure

```
src/lib/quick-note/
  └── open-quick-note.ts      — Shared open action used by all entry points

src/components/items/
  └── QuickNoteDialog.tsx    — Dialog with title + content form
  └── QuickNoteDialog.test.tsx — Tests for form submission, validation, success/error flows
```

## TanStack Form Usage

Use `useForm` from `@tanstack/react-form` to manage form state and validation:

```typescript
import { useForm } from '@tanstack/react-form'
import { Loader2 } from 'lucide-react'

const form = useForm({
  defaultValues: {
    title: '',
    content: '',
  },
  onSubmit: async ({ value }) => {
    await createItem({
      title: value.title,
      content: value.content,
      content_type: 'note',
    })
  },
})

// In JSX — use form.Field for each input:
<form.Field
  name="title"
  validators={{
    onSubmit: ({ value }) => !value.trim() ? t('notes.create.titleRequired') : undefined,
  }}
>
  {(field) => (
    <>
      <Input
        value={field.state.value}
        onChange={(e) => field.handleChange(e.target.value)}
        onBlur={field.handleBlur}
      />
      {field.state.meta.errors.length > 0 && (
        <p className="text-sm text-destructive">{field.state.meta.errors[0]}</p>
      )}
    </>
  )}
</form.Field>

<form.Field
  name="content"
  validators={{
    onSubmit: ({ value }) => !value.trim() ? t('notes.create.contentRequired') : undefined,
  }}
>
  {(field) => (
    <>
      <Textarea
        value={field.state.value}
        onChange={(e) => field.handleChange(e.target.value)}
        onBlur={field.handleBlur}
      />
      {field.state.meta.errors.length > 0 && (
        <p className="text-sm text-destructive">{field.state.meta.errors[0]}</p>
      )}
    </>
  )}
</form.Field>

// Reset form on dialog close or after successful submission:
form.reset()

// Submit:
<form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
  {([canSubmit, isSubmitting]) => (
    <Button type="submit" disabled={!canSubmit || isSubmitting}>
      {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
      {isSubmitting ? t('notes.create.saving') : t('notes.create.submit')}
    </Button>
  )}
</form.Subscribe>
```

## Shared Open Action

Create `src/lib/quick-note/open-quick-note.ts`:

```typescript
import { useUIStore } from '@/store/ui-store'

export function openQuickNoteDialog(): void {
  useUIStore.getState().setQuickNoteDialogOpen(true)
}
```

## UIStore Addition

Add to `src/store/ui-store.ts` following the existing `preferencesOpen` / `commandPaletteOpen` pattern:

```typescript
// In UIState interface:
quickNoteDialogOpen: boolean
toggleQuickNoteDialog: () => void
setQuickNoteDialogOpen: (open: boolean) => void

// In store implementation:
quickNoteDialogOpen: false,

toggleQuickNoteDialog: () =>
  set(
    state => ({ quickNoteDialogOpen: !state.quickNoteDialogOpen }),
    undefined,
    'toggleQuickNoteDialog'
  ),

setQuickNoteDialogOpen: open =>
  set({ quickNoteDialogOpen: open }, undefined, 'setQuickNoteDialogOpen'),
```

## Command Registration

Create `src/lib/commands/note-commands.ts` following the pattern in `navigation-commands.ts`:

```typescript
import { NotebookPen } from 'lucide-react'
import { openQuickNoteDialog } from '@/lib/quick-note/open-quick-note'
import type { AppCommand } from './types'

export const noteCommands: AppCommand[] = [
  {
    id: 'create-note',
    labelKey: 'commands.createNote.label',
    descriptionKey: 'commands.createNote.description',
    icon: NotebookPen,
    group: 'notes',
    shortcut: '⌘+N',
    keywords: ['note', 'create', 'new', 'write'],
    execute: () => {
      openQuickNoteDialog()
    },
  },
]
```

## Keyboard Shortcut Registration

Add `Cmd+N` handler to `src/hooks/use-keyboard-shortcuts.ts` (shortcuts are registered here, not auto-bound from commands):

```typescript
case 'n': {
  e.preventDefault()
  openQuickNoteDialog()
  break
}
```

## Translation Keys

Add to `locales/en.json`:

```json
{
  "notes.create.title": "New Note",
  "notes.create.openButton": "New Note",
  "notes.create.titleLabel": "Title",
  "notes.create.titlePlaceholder": "Note title",
  "notes.create.contentLabel": "Content",
  "notes.create.contentPlaceholder": "Write your note... (Markdown supported)",
  "notes.create.submit": "Save Note",
  "notes.create.cancel": "Cancel",
  "notes.create.saving": "Saving...",
  "notes.create.success": "Note saved",
  "notes.create.error": "Failed to save note",
  "notes.create.titleRequired": "Title is required",
  "notes.create.contentRequired": "Content is required",
  "commands.createNote.label": "Create New Note",
  "commands.createNote.description": "Open the quick note creation dialog",
  "commands.group.notes": "Notes"
}
```

Add corresponding Chinese translations to `locales/zh.json`.

## Documentation Update

Update `docs/developer/core-systems/keyboard-shortcuts.md` to include the new `Cmd/Ctrl+N` quick-note shortcut.

## Files to Create/Modify

**Create:**

- `src/lib/quick-note/open-quick-note.ts` — Shared quick-note open action
- `src/lib/commands/note-commands.ts` — Note command definitions
- `src/components/items/QuickNoteDialog.tsx` — Note creation dialog
- `src/components/items/QuickNoteDialog.test.tsx` — Tests for dialog

**Modify:**

- `src/store/ui-store.ts` — Add `quickNoteDialogOpen` state, toggle, and setter
- `src/store/ui-store.test.ts` — Add quick-note dialog state tests
- `src/hooks/use-keyboard-shortcuts.ts` — Add `Cmd+N` handler
- `src/hooks/use-keyboard-shortcuts.test.ts` — Verify `Cmd/Ctrl+N` behavior
- `src/lib/commands/index.ts` — Import `noteCommands` and add `registerCommands(noteCommands)` to `initializeCommandSystem()`
- `src/lib/commands/commands.test.ts` (or add `note-commands.test.ts`) — Verify command availability and execution
- `src/components/layout/LeftSideBar.tsx` — Add "New Note" button
- `src/components/layout/MainWindowShell.tsx` — Mount `QuickNoteDialog` as global overlay
- `locales/en.json` — Add translation keys
- `locales/zh.json` — Add Chinese translations
- `docs/developer/core-systems/keyboard-shortcuts.md` — Add `Cmd/Ctrl+N`

## Test Coverage

`src/components/items/QuickNoteDialog.test.tsx` should cover:

- Form submission calls `useCreateItem` mutation with correct `title`, `content`, and `content_type: 'note'`
- TanStack Form validation prevents submission with empty title or content, showing field-level errors
- Success: dialog closes, `form.reset()` clears fields, and success notification is shown
- Error: form state is preserved (TanStack Form retains values) and error notification is shown
- Loading state: submit button is disabled via `form.Subscribe` (`isSubmitting` / `canSubmit`)
- Loading state: spinner icon is visible during submission
- Form resets when dialog closes

Additional required tests:

- `src/store/ui-store.test.ts`: quick note open/toggle/set behavior
- `src/hooks/use-keyboard-shortcuts.test.ts`: `Cmd/Ctrl+N` opens dialog
- `src/lib/commands/commands.test.ts` (or `note-commands.test.ts`): `create-note` command opens dialog

## Verification

```bash
bun run typecheck
bun run lint
bun run test:run
bun run check:all
```

---

## Implementation Details

_Tracked: 2026-02-13_

### Files Changed

| File | Change | Description |
| --- | --- | --- |
| `src/components/items/QuickNoteDialog.tsx` | Created | Dialog component with TanStack Form, validation, success/error handling |
| `src/components/items/QuickNoteDialog.test.tsx` | Created | 5 tests: submit, validation, error, loading/spinner, form reset |
| `src/lib/quick-note/open-quick-note.ts` | Created | Shared `openQuickNoteDialog()` helper using `getState()` pattern |
| `src/lib/commands/note-commands.ts` | Created | `create-note` command with icon, shortcut, keywords |
| `src/lib/commands/note-commands.test.ts` | Created | Tests for command metadata and execute behavior |
| `src/hooks/use-keyboard-shortcuts.test.ts` | Created | Tests for Cmd+N, Ctrl+N, and guard conditions (palette/prefs open) |
| `src/store/ui-store.ts` | Modified | Added `quickNoteDialogOpen` state, toggle, and setter |
| `src/store/ui-store.test.ts` | Modified | Added toggle and set tests for quick note dialog state |
| `src/hooks/use-keyboard-shortcuts.ts` | Modified | Added `Cmd/Ctrl+N` handler with modal guard |
| `src/hooks/useMainWindowEventListeners.ts` | Modified | Updated JSDoc comment to list Cmd+N |
| `src/lib/commands/index.ts` | Modified | Imported and registered `noteCommands` |
| `src/components/layout/LeftSideBar.tsx` | Modified | Added "New Note" button wired to `openQuickNoteDialog()` |
| `src/components/layout/MainWindowShell.tsx` | Modified | Mounted `<QuickNoteDialog />` as global overlay |
| `src/components/items/index.ts` | Modified | Added `QuickNoteDialog` barrel export |
| `locales/en.json` | Modified | Added 16 translation keys (notes.create.*, commands.createNote.*, commands.group.notes) |
| `locales/zh.json` | Modified | Added corresponding Chinese translations |
| `package.json` | Modified | Added `@tanstack/react-form@^1.28.1` dependency |
| `docs/developer/core-systems/keyboard-shortcuts.md` | Modified | Added Cmd+N to shortcut table and architecture code example |

### Dependencies Added

- `@tanstack/react-form@^1.28.1` - Form state management and field-level validation for the note creation form

---

## Learning Report

_Generated: 2026-02-13_

### Summary

Implemented the Quick Note Creation UI — a modal dialog accessible from three entry points (sidebar button, command palette, keyboard shortcut `Cmd/Ctrl+N`) that allows users to create text notes with title and content fields. The implementation spans 18 files (7 created, 11 modified) with comprehensive test coverage across dialog behavior, store state, keyboard shortcuts, and command registration.

### Patterns & Decisions

1. **State Management Onion applied correctly**: Dialog open/close state uses Zustand (`quickNoteDialogOpen` in UIStore) since it's needed across components (command system, sidebar, keyboard shortcuts all trigger it). Form state uses TanStack Form (component-local). Submission uses TanStack Query's `useCreateItem()` mutation (persistent data). This follows the documented `useState → Zustand → TanStack Query` decision tree.

2. **Shared open action via `getState()`**: Created `src/lib/quick-note/open-quick-note.ts` as a single function that uses `useUIStore.getState().setQuickNoteDialogOpen(true)`. All three entry points call this same function, preventing drift. This follows the `getState()` pattern for callbacks documented in `AGENTS.md`.

3. **Selector syntax enforced**: The dialog component reads UIStore with `useUIStore(state => state.quickNoteDialogOpen)` and `useUIStore(state => state.setQuickNoteDialogOpen)` — two separate selectors rather than destructuring. This prevents render cascades and satisfies the ast-grep rule.

4. **Keyboard shortcut guard logic**: The `Cmd+N` handler checks `commandPaletteOpen`, `preferencesOpen`, and `quickNoteDialogOpen` before opening the dialog. This prevents the shortcut from firing when another modal is already active. `preventDefault()` is called before the guard check to always suppress browser default behavior.

5. **TanStack Form integration**: Used `useForm` with `onSubmit` validators (not `onChange`) to avoid premature validation. The `form.Subscribe` selector pattern `[state.canSubmit, state.isSubmitting]` provides the loading state for the submit button. `form.reset()` is called on both success and dialog close.

6. **Cmd+Enter to submit**: Added `onKeyDown` handler on the textarea for `Cmd/Ctrl+Enter` to submit the form — a common UX pattern for text editors not specified in the task but natural for note-taking.

### Challenges & Solutions

1. **TanStack Form error type handling**: `field.state.meta.errors` returns an array of unknown types (could be strings, objects, or validation results depending on version). Solved by creating a `getFieldError()` helper that safely extracts string errors, avoiding type assertion issues.

2. **Test mocking with async imports**: TanStack Form and React rendering required careful mock setup. Used `vi.mock()` with `vi.importActual()` for `@/services/items` to keep all other exports intact while mocking `useCreateItem`. The `await import()` pattern after `vi.mock()` ensures correct module resolution order.

3. **Form submission in tests**: TanStack Form's async submission required `waitFor()` wrappers around assertions since `form.handleSubmit()` returns a promise. The loading state test used a deferred promise pattern (`new Promise(resolve => { resolveMutation = resolve })`) to assert the intermediate loading state before resolving.

### Lessons Learned

1. **What worked well**: The task spec was exceptionally detailed — it provided exact code snippets for UIStore additions, command registration, TanStack Form usage, and translation keys. This made implementation straightforward with minimal ambiguity. Future tasks should follow this level of specificity.

2. **TanStack Form is lightweight for simple forms**: For a two-field form, TanStack Form adds some ceremony (render prop pattern with `form.Field`, `form.Subscribe`), but provides field-level validation, `isSubmitting` tracking, and `canSubmit` state for free. The forward-compatibility argument (richer capture forms later) justifies the dependency.

3. **Three entry points, one action**: The shared `openQuickNoteDialog()` pattern is the right approach. Without it, the sidebar button, command palette command, and keyboard shortcut would each need to import and call `useUIStore.getState().setQuickNoteDialogOpen(true)` independently — a maintenance risk.

4. **Test coverage for guard conditions**: Testing that `Cmd+N` does NOT open the dialog when other modals are open is just as important as testing that it does. The keyboard shortcuts test file covers 5 scenarios including 3 guard conditions.

### Documentation Impact

- **Updated**: `docs/developer/core-systems/keyboard-shortcuts.md` — Added `Cmd+N` to the shortcut table and updated the architecture code example.
- **Potentially useful**: A brief section on TanStack Form patterns could be added to developer docs if more forms are built. Currently one form doesn't justify standalone documentation.
- **No gaps found**: The existing state management docs, command system docs, and i18n patterns docs were sufficient for this implementation.
