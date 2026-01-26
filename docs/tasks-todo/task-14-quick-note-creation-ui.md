# Task: Implement Quick Note Creation UI

## Summary

Build the quick note creation interface that allows users to write and save text notes from the desktop app. Includes a simple form with title and content fields, Markdown support in content, and immediate save to the backend. Uses `useState` for form state and TanStack Query mutation for submission.

## Acceptance Criteria

- [ ] Quick note creation accessible from the sidebar (button or shortcut)
- [ ] Note creation form with: title input (required), content textarea (required, Markdown supported)
- [ ] Content type automatically set to `'note'`
- [ ] Submit button saves note via `useCreateItem()` mutation
- [ ] Success: form clears, toast notification shown, item list refreshed
- [ ] Error: error message displayed, form preserved for retry
- [ ] Loading state: submit button disabled with spinner during save
- [ ] Keyboard shortcut: Cmd+N or similar to open quick note (register in command system)
- [ ] Form state uses `useState` (component-local, not shared)
- [ ] All user-facing strings use i18n translation keys

## Dependencies

- Task 12: TanStack Query service hooks (`useCreateItem()`)
- Task 13: Item list (to verify created items appear)
- Phase 1: Sidebar layout, command system, i18n, toast notifications (`sonner`)

## Technical Notes

- Per state management decision tree: form input values use `useState` (component-local)
- Per state management decision tree: submission uses TanStack Query (persistent data)
- The sidebar already has placeholder navigation — add a "New Note" button
- Use shadcn/ui components: `Dialog` or inline form, `Input`, `Textarea`, `Button`
- Per `docs/developer/core-systems/command-system.md`: register keyboard shortcut with `labelKey`
- The quick note could be a dialog (modal) or an inline form — dialog is simpler for MVP
- Markdown rendering is not needed at creation time — just a plain textarea that accepts Markdown

## Component Structure

```
src/components/items/
  └── QuickNoteDialog.tsx    — Dialog with title + content form
```

## Command Registration

```typescript
// In src/lib/commands/ — add to existing navigation-commands.ts or create note-commands.ts
{
  id: 'create-note',
  labelKey: 'commands.createNote',
  shortcut: { key: 'n', meta: true },
  action: () => { /* open quick note dialog */ },
}
```

## Translation Keys

Add to `/locales/en.json`:

```json
{
  "notes.create.title": "New Note",
  "notes.create.titleField": "Title",
  "notes.create.titlePlaceholder": "Note title",
  "notes.create.contentField": "Content",
  "notes.create.contentPlaceholder": "Write your note... (Markdown supported)",
  "notes.create.submit": "Save Note",
  "notes.create.saving": "Saving...",
  "notes.create.success": "Note saved",
  "notes.create.error": "Failed to save note",
  "commands.createNote": "Create New Note"
}
```

## Files to Create/Modify

**Create:**

- `src/components/items/QuickNoteDialog.tsx` — Note creation dialog

**Modify:**

- `src/components/layout/LeftSideBar.tsx` — Add "New Note" button
- `src/lib/commands/navigation-commands.ts` (or create `note-commands.ts`) — Register Cmd+N shortcut
- `locales/en.json` — Add translation keys
- `locales/zh-CN.json` — Add Chinese translations

## Verification

```bash
bun run typecheck
bun run lint
bun run test
bun run check:all
```
