# Task: Implement File Import Dialog

## Summary

Build a file import dialog that allows users to select text and Markdown files from their filesystem and import them as items. Uses Tauri's file dialog API for native file selection and reads file content through Rust commands.

## Acceptance Criteria

- [ ] File import accessible from sidebar or menu (Import button)
- [ ] Opens native file selection dialog (Tauri `dialog.open()`)
- [ ] Filters for supported file types: `.txt`, `.md`, `.markdown`
- [ ] Reads selected file content via Tauri file system commands
- [ ] Creates item via `useCreateItem()` with `content_type: 'file'`
- [ ] Title defaults to filename (without extension)
- [ ] Success: toast notification, item list refreshed
- [ ] Error: error message if file read fails or backend rejects
- [ ] Loading state during file read and submission
- [ ] Supports selecting a single file (batch import out of scope per MVP plan)
- [ ] All user-facing strings use i18n translation keys

## Dependencies

- Task 12: TanStack Query service hooks (`useCreateItem()`)
- Task 13: Item list (to verify imported items appear)
- Phase 1: Tauri bindings, dialog plugin

## Technical Notes

- Use `@tauri-apps/plugin-dialog` for file selection: `open({ filters: [{ name: 'Text', extensions: ['txt', 'md', 'markdown'] }] })`
- Use `@tauri-apps/plugin-fs` or a Rust command to read file content
- Per MVP plan: "File Import excludes: Drag-and-drop, Watch folders, Batch import UI"
- Content type detection: `.md`/`.markdown` → `'file'` (Markdown), `.txt` → `'file'` (plain text)
- If using a Rust command for file reading, run `bun run rust:bindings` afterward
- The import could be triggered from sidebar or from command palette

## Translation Keys

Add to `/locales/en.json`:

```json
{
  "import.button": "Import File",
  "import.title": "Import File",
  "import.selectFile": "Select a file to import",
  "import.supportedTypes": "Supported: .txt, .md, .markdown",
  "import.importing": "Importing...",
  "import.success": "File imported successfully",
  "import.error": "Failed to import file",
  "import.readError": "Could not read file"
}
```

## Files to Create/Modify

**Create:**

- `src/components/items/FileImportButton.tsx` — Import button with file dialog logic

**Modify:**

- `src/components/layout/LeftSideBar.tsx` — Add import button
- `locales/en.json` — Add translation keys
- `locales/zh-CN.json` — Add Chinese translations

## Verification

```bash
bun run typecheck
bun run lint
bun run test
bun run check:all
```
