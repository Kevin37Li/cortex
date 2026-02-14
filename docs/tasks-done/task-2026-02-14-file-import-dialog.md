# Task: Implement File Import Dialog

## Summary

Build a file import workflow that allows users to select text and Markdown files from their filesystem and import them as items. The workflow must be reusable from both the sidebar button and command palette command (no React hooks in command execution). Use Tauri's `@tauri-apps/plugin-dialog` for native file selection and `@tauri-apps/plugin-fs` for file metadata/content access.

## Acceptance Criteria

- [x] File import accessible from sidebar (Import button) and command palette
- [x] Shared import action used by both sidebar UI and command palette command (single source of truth)
- [x] Opens native file selection dialog (Tauri `dialog.open()`)
- [x] Filters for supported file types: `.txt`, `.md`, `.markdown`
- [x] Reads selected file content via `readTextFile` from `@tauri-apps/plugin-fs`
- [x] Validates file size does not exceed 5MB before reading (via file `stat` metadata)
- [x] Creates item with `content_type: 'file'` via a non-hook service function reusable outside React
- [x] Title defaults to filename (without extension)
- [x] Success: notification via `notifications.success()` from `@/lib/notifications`, item list refreshed
- [x] Error: notification via `notifications.error()` from `@/lib/notifications`, logged via `logger.error()`
- [x] Loading state during file read (`useState`) and submission (`useCreateItem().isPending`)
- [x] Supports selecting a single file (batch import out of scope per MVP plan)
- [x] User canceling the file dialog exits without errors or notifications
- [x] All user-facing strings use i18n translation keys
- [x] Import command registered in command system
- [x] Command coverage includes metadata and execute-path test(s)

## Dependencies

- Task 12: TanStack Query service hooks (`useCreateItem()`)
- Task 13: Item list (to verify imported items appear)
- Phase 1: Tauri bindings, dialog plugin

## Technical Notes

- Use `@tauri-apps/plugin-dialog` for file selection: `open({ filters: [{ name: 'Text', extensions: ['txt', 'md', 'markdown'] }] })`
- Use `stat` + `readTextFile` from `@tauri-apps/plugin-fs` (already installed with permissions configured in `src-tauri/capabilities/default.json`)
- Per MVP plan: "File Import excludes: Drag-and-drop, Watch folders, Batch import UI"
- All supported extensions (`.md`, `.markdown`, `.txt`) map to `content_type: 'file'`
- File size limit: 5MB — validate using `stat(path).size` before reading, show `items.import.fileTooLarge` error if exceeded
- Create a shared non-hook import helper (e.g., `src/lib/file-import/import-file.ts`) so commands can execute import logic without hooks
- Expose non-hook create API in `src/services/items.ts` (e.g., `createItem`) and keep `useCreateItem()` as the TanStack Query wrapper around that function
- Command module (`src/lib/commands/import-commands.ts`) must call shared helper/service, not hooks
- Handle `open()` cancellation (`null`) as a no-op
- Normalize filename from path for both POSIX and Windows separators, then strip extension for default title
- **Error handling**: Use Pattern 1 (Explicit Handling) — `notifications.error(t('items.import.error'))` for user feedback, `logger.error()` for logging
- **State management**: Import loading/error state is component-local (`useState`). Item creation state comes from `useCreateItem().isPending`. Do not use Zustand for import-specific state.
- **Command system**: Register an `import-file` command following the pattern in `src/lib/commands/note-commands.ts`. Place it in the `notes` command group (content creation actions).

## Translation Keys

Add to `/locales/en.json`:

```json
{
  "items.import.button": "Import File",
  "items.import.title": "Import File",
  "items.import.selectFile": "Select a file to import",
  "items.import.supportedTypes": "Supported: .txt, .md, .markdown",
  "items.import.importing": "Importing...",
  "items.import.success": "File imported successfully",
  "items.import.error": "Failed to import file",
  "items.import.readError": "Could not read file",
  "items.import.fileTooLarge": "File is too large (max {{maxSize}})",
  "commands.importFile.label": "Import File",
  "commands.importFile.description": "Import a text or Markdown file as an item"
}
```

Add corresponding Chinese translations to `/locales/zh.json`.

## Files to Create/Modify

**Create:**

- `src/lib/file-import/import-file.ts` — Shared import workflow (dialog → validate size → read content → create item)
- `src/lib/file-import/import-file.test.ts` — Unit tests for shared import workflow and edge cases
- `src/components/items/FileImportButton.tsx` — Import button with file dialog logic
- `src/components/items/FileImportButton.test.tsx` — Tests: dialog open, user cancellation, successful import, read errors, file size validation, i18n usage
- `src/lib/commands/import-commands.ts` — Import file command (follows `note-commands.ts` pattern)
- `src/lib/commands/import-commands.test.ts` — Import command metadata and execute-path tests

**Modify:**

- `src/services/items.ts` — Add non-hook `createItem` function reused by `useCreateItem()` and import workflow
- `src/services/items.test.ts` — Add coverage for new `createItem` function
- `src/components/layout/LeftSideBar.tsx` — Add import button
- `src/components/items/index.ts` — Export `FileImportButton`
- `src/lib/commands/index.ts` — Import and register `importCommands`
- `src/test/setup.ts` — Add mocks for `@tauri-apps/plugin-dialog` (`open`) and `@tauri-apps/plugin-fs` (`readTextFile`, `stat`)
- `locales/en.json` — Add translation keys
- `locales/zh.json` — Add Chinese translations

## Verification

```bash
bun run typecheck
bun run lint
bun run test:run
bun run check:all
```

---

## Implementation Details

_Tracked: 2026-02-14_

### Files Changed

| File                                        | Change   | Description                                                                                 |
| ------------------------------------------- | -------- | ------------------------------------------------------------------------------------------- |
| `src/lib/file-import/import-file.ts`        | Created  | Added shared import workflow (dialog, size validation, text read, create item, notifications). |
| `src/lib/file-import/import-file.test.ts`   | Created  | Added unit tests for cancellation, size validation, read failures, create failures, and title parsing. |
| `src/lib/file-import/index.ts`              | Created  | Added public exports for file-import workflow helpers and types.                            |
| `src/components/items/FileImportButton.tsx` | Created  | Added sidebar import button with combined loading state (`useState` + `useCreateItem().isPending`). |
| `src/components/items/FileImportButton.test.tsx` | Created  | Added component tests for dialog options, cancellation behavior, success/error paths, and i18n rendering. |
| `src/lib/commands/import-commands.ts`       | Created  | Added `import-file` command using shared import workflow and non-hook `createItem` service. |
| `src/lib/commands/import-commands.test.ts`  | Created  | Added command metadata and execute-path tests for imported/cancelled/failed flows.         |
| `src/services/items.ts`                     | Modified | Added reusable non-hook `createItem` API and wired `useCreateItem()` to reuse it.          |
| `src/services/items.test.ts`                | Modified | Added coverage for new `createItem` service function request behavior.                      |
| `src/components/layout/LeftSideBar.tsx`     | Modified | Added `FileImportButton` under quick note action.                                           |
| `src/components/items/index.ts`             | Modified | Exported `FileImportButton`.                                                                |
| `src/lib/commands/index.ts`                 | Modified | Registered and exported `importCommands`.                                                   |
| `src/test/setup.ts`                         | Modified | Added test mocks for `@tauri-apps/plugin-dialog` and `@tauri-apps/plugin-fs`.              |
| `locales/en.json`                           | Modified | Added file import and command palette translation keys (English).                           |
| `locales/zh.json`                           | Modified | Added file import and command palette translation keys (Chinese).                           |
| `docs/tasks-todo/task-15-file-import-dialog.md` | Modified | Updated task requirements during implementation and recorded completion details.             |

### Dependencies Added

- None.

### Verification

- `bun run check:all` passed (typecheck, lint, ast-grep, format checks, Rust checks, Python checks, TS tests, Rust tests, Python tests).

---

## Learning Report

_Generated: 2026-02-14_

### Summary

Implemented a shared file import workflow that is reusable by both UI components and command execution paths, while preserving architecture constraints (no hooks in command execution). The task is fully covered by component, command, service, and workflow tests.

### Patterns and Decisions

- Centralized import behavior in `src/lib/file-import/import-file.ts` to enforce a single source of truth across sidebar and command palette entry points.
- Added a non-hook `createItem` function in `src/services/items.ts` so command execution can create items without violating React hook rules.
- Kept import read-state local to `FileImportButton` and used `useCreateItem().isPending` for mutation state, matching the state ownership model.
- Used translation keys for all import-facing UI/notification strings and command metadata labels/descriptions.

### Challenges and Solutions

- Needed seamless loading behavior across two async phases (file read + mutation): solved by combining local `readingFile` state with mutation pending state and handing control between them.
- Needed robust cross-platform title extraction: solved by normalizing separators and stripping extensions via dedicated helpers.
- Needed testability of native dialog/fs operations: solved by dependency injection in import workflow options plus global test setup mocks.

### Lessons Learned

- Shared workflow modules with injectable dependencies improve reuse and make command/UI parity easier to guarantee.
- Non-hook service functions are essential when moving logic into command handlers.
- Adding capability-specific mocks in `src/test/setup.ts` early reduces friction for feature-level test expansion.
