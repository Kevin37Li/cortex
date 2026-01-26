# Task: Verify and Complete Phase 1 Translation Keys

## Summary

Audit existing translation keys, add missing strings for Phase 1 UI components, and create Chinese (Simplified) translations.

## Acceptance Criteria

- [ ] All Phase 1 UI strings use translation keys (no hardcoded strings)
- [ ] Navigation labels verified (`nav.allItems`, `nav.conversations`, `nav.settings`)
- [ ] Empty states translated
- [ ] Error messages translated (including ErrorBoundary)
- [ ] Settings labels translated
- [ ] CSS logical properties verified (for future RTL support)
- [ ] Chinese translation file created and complete

## Dependencies

- Task 9: Frontend routing and navigation (for nav labels) - COMPLETED

## Technical Notes

- Follow patterns in `docs/developer/ui-ux/i18n-patterns.md`
- Use `useTranslation` hook in React components
- Use `i18n.t()` in non-React code
- CSS should use `text-start`/`text-end` not `text-left`/`text-right`
- CSS should use `ps-*`/`pe-*` not `pl-*`/`pr-*`
- CSS should use `ms-*`/`me-*` not `ml-*`/`mr-*`

## Audit Checklist

### Existing Components (verify keys exist and are used)

- [ ] `src/components/command-palette/CommandPalette.tsx` - uses `t('commandPalette.*')`
- [ ] `src/components/preferences/PreferencesDialog.tsx` - uses `t('preferences.*')`
- [ ] `src/components/titlebar/TitleBar.tsx` - uses `t('titlebar.*')`
- [ ] `src/components/layout/LeftSideBar.tsx` - uses `t(item.labelKey)` for nav

### Components Needing i18n (add keys)

- [ ] `src/components/ErrorBoundary.tsx` - has 5 hardcoded English strings:
  - Line 100-101: "Something went wrong"
  - Line 103-106: "The application encountered an unexpected error..."
  - Line 115: "Reload Application"
  - Line 120: "Try Again"
  - Line 127: "Error Details (Development Only)"

### Route Components (verify keys exist)

- [ ] `src/routes/items/index.tsx` - empty state
- [ ] `src/routes/conversations/index.tsx` - empty state
- [ ] `src/routes/$.tsx` - not found page

## Translation Keys to Add

### New keys for ErrorBoundary

```json
{
  "errorBoundary": {
    "title": "Something went wrong",
    "description": "The application encountered an unexpected error. You can try reloading or attempting the action again.",
    "reloadButton": "Reload Application",
    "retryButton": "Try Again",
    "detailsTitle": "Error Details (Development Only)"
  }
}
```

### Keys already in en.json (verify usage)

These keys exist but need to be verified they're being used:

- `nav.allItems`, `nav.conversations`, `nav.settings`
- `items.emptyState`
- `conversations.emptyState`
- `notFound.title`, `notFound.description`, `notFound.backToItems`
- `commands.goToItems.*`, `commands.goToConversations.*`, `commands.goToSettings.*`

## CSS Logical Properties Audit

Fix these files to use CSS logical properties:

| File                                                    | Current     | Replace With |
| ------------------------------------------------------- | ----------- | ------------ |
| `src/components/ErrorBoundary.tsx:126`                  | `text-left` | `text-start` |
| `src/components/titlebar/TitleBar.tsx:58`               | `pl-2`      | `ps-2`       |
| `src/components/titlebar/TitleBar.tsx:93`               | `pr-2`      | `pe-2`       |
| `src/components/titlebar/LinuxTitleBar.tsx:32`          | `pl-2`      | `ps-2`       |
| `src/components/titlebar/LinuxTitleBar.tsx:40`          | `pr-2`      | `pe-2`       |
| `src/components/command-palette/CommandPalette.tsx:104` | `mr-2`      | `me-2`       |
| `src/components/command-palette/CommandPalette.tsx:107` | `ml-auto`   | `ms-auto`    |

Note: shadcn/ui components may have physical properties - these are acceptable as they're external primitives.

## Files to Modify

- `locales/en.json` - Add `errorBoundary.*` keys
- `locales/zh.json` - Create with all translations (Chinese Simplified)
- `src/components/ErrorBoundary.tsx` - Use `i18n.t()` directly (class component, cannot use hooks), replace hardcoded strings
- `src/i18n/config.ts` - Add Chinese language to supported languages

## Files to Delete

- `locales/ar.json` - Remove Arabic (not needed)
- `locales/fr.json` - Remove French (not needed)

## Implementation Steps

1. **Add ErrorBoundary keys to en.json**
2. **Create zh.json** with all translations from en.json
3. **Update ErrorBoundary.tsx** to use translation keys
4. **Update i18n config** to include Chinese, remove Arabic/French
5. **Fix CSS logical properties** in listed files
6. **Delete ar.json and fr.json**
7. **Test language switching** in preferences

## Chinese Translations Reference

Key translations for zh.json (Simplified Chinese):

```json
{
  "app.name": "Cortex",
  "nav.allItems": "所有项目",
  "nav.conversations": "对话",
  "nav.settings": "设置",
  "items.emptyState": "暂无项目。开始添加您的第一个项目。",
  "conversations.emptyState": "暂无对话。开始新的对话。",
  "notFound.title": "页面未找到",
  "notFound.description": "您要查找的页面不存在。",
  "notFound.backToItems": "返回项目",
  "preferences.title": "偏好设置",
  "preferences.general": "通用",
  "preferences.appearance": "外观",
  "preferences.advanced": "高级",
  "common.enabled": "已启用",
  "common.disabled": "已禁用",
  "common.reset": "重置",
  "errorBoundary.title": "出错了",
  "errorBoundary.description": "应用程序遇到意外错误。您可以尝试重新加载或再次执行操作。",
  "errorBoundary.reloadButton": "重新加载应用",
  "errorBoundary.retryButton": "重试",
  "errorBoundary.detailsTitle": "错误详情（仅开发模式）"
}
```

## Verification

1. Switch language to Chinese in preferences
2. All UI text updates to Chinese
3. No console warnings about missing translation keys
4. ErrorBoundary displays translated text when triggered
5. Run `bun run check:all` passes

---

## Implementation Details

_Tracked: 2026-01-25_

### Files Changed

| File                                                      | Change   | Description                                                                                                                  |
| --------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `locales/en.json`                                         | Modified | Added 5 `errorBoundary.*` translation keys                                                                                   |
| `locales/zh.json`                                         | Created  | Complete Chinese (Simplified) translation file with all 139 lines matching en.json keys                                      |
| `locales/ar.json`                                         | Deleted  | Removed unused Arabic locale                                                                                                 |
| `locales/fr.json`                                         | Deleted  | Removed unused French locale                                                                                                 |
| `src/components/ErrorBoundary.tsx`                        | Modified | Imported `i18n` from config, replaced 5 hardcoded English strings with `i18n.t()` calls, changed `text-left` to `text-start` |
| `src/i18n/config.ts`                                      | Modified | Replaced `ar`/`fr` imports with `zh` import, updated `resources` map to `en`+`zh` only                                       |
| `src/components/titlebar/TitleBar.tsx`                    | Modified | `pl-2` → `ps-2`, `pr-2` → `pe-2` (CSS logical properties)                                                                    |
| `src/components/titlebar/LinuxTitleBar.tsx`               | Modified | `pl-2` → `ps-2`, `pr-2` → `pe-2` (CSS logical properties)                                                                    |
| `src/components/command-palette/CommandPalette.tsx`       | Modified | `mr-2` → `me-2`, `ml-auto` → `ms-auto` (CSS logical properties)                                                              |
| `docs/tasks-todo/task-10-i18n-translation-keys-phase1.md` | Modified | Fixed doc to say `i18n.t()` instead of `useTranslation` for class component                                                  |

### Dependencies Added

None.

### Acceptance Criteria Status

- [x] All Phase 1 UI strings use translation keys (no hardcoded strings) — `ErrorBoundary.tsx` was the last component with hardcoded strings, now uses `i18n.t()`
- [x] Navigation labels verified (`nav.allItems`, `nav.conversations`, `nav.settings`) — present in `en.json:4-6` and `zh.json:4-6`
- [x] Empty states translated — `items.emptyState` and `conversations.emptyState` in both locales
- [x] Error messages translated (including ErrorBoundary) — `errorBoundary.*` keys added to both locales, used in `ErrorBoundary.tsx:102-128`
- [x] Settings labels translated — `preferences.*` keys present in both locales
- [x] CSS logical properties verified (for future RTL support) — 7 physical properties converted across 4 files
- [x] Chinese translation file created and complete — `locales/zh.json` (139 lines, all keys from en.json)

---

## Learning Report

_Generated: 2026-01-25_

### Summary

Completed Phase 1 i18n translation key verification and addition. The implementation touched 9 files: added ErrorBoundary translation keys to `en.json`, created a complete `zh.json` Chinese locale, internationalized the `ErrorBoundary` class component, cleaned up unused locale files (`ar.json`, `fr.json`), updated `i18n/config.ts` to register Chinese, and converted 7 physical CSS properties to logical equivalents across 3 components. All 39 frontend tests, 4 Rust tests, and 89 Python tests pass. All linters, formatters, and static analysis checks pass.

### Patterns & Decisions

1. **`i18n.t()` for class components**: `ErrorBoundary` is a React class component (required for `getDerivedStateFromError`), so it cannot use the `useTranslation` hook. The direct `i18n.t()` import pattern was used instead, following the established pattern documented in `AGENTS.md` ("Non-React contexts - bind for many calls, or use directly"). This is acceptable because the error boundary only renders on crashes, and reactive language switching mid-error-screen is not a meaningful use case.

2. **CSS logical properties**: Physical properties (`pl-`, `pr-`, `ml-`, `mr-`, `text-left`) were converted to logical equivalents (`ps-`, `pe-`, `ms-`, `me-`, `text-start`). This follows Tailwind v4's logical property support and prepares the app for future RTL language support without any functional change for LTR layouts.

3. **Locale cleanup**: Arabic and French locales were removed since they were placeholder translations not needed for the current two-language scope (English + Chinese). The RTL language list in `config.ts` was kept for future expansion.

4. **Complete zh.json**: The Chinese translation file includes all 139 lines with every key from `en.json`, including detail view keys (`items.detail.*`, `conversations.detail.*`) that were not in the original task reference section. This ensures no missing key warnings.

### Challenges & Solutions

1. **Task doc vs implementation mismatch**: The task document originally instructed to "Add useTranslation hook" for `ErrorBoundary.tsx`, which is impossible for a class component. This was caught during CodeRabbit review and the task doc was corrected to reference `i18n.t()`. Future task specs should note component type when specifying i18n approach.

2. **No reactive language switching in ErrorBoundary**: Using `i18n.t()` directly means the ErrorBoundary won't automatically re-render when the language changes. This is a known and acceptable limitation — the error screen only appears during crashes, and a page reload (which the UI suggests) would pick up the new language anyway.

### Lessons Learned

1. **Verify component type before specifying i18n approach**: Hooks (`useTranslation`) vs direct imports (`i18n.t()`) vs HOC (`withTranslation`) depend on whether the component is functional or class-based. Task specs should note this.

2. **CSS logical property migration is mechanical**: The 7 property conversions were straightforward find-and-replace operations. A codemod or ast-grep rule could enforce this pattern going forward to prevent new physical properties from being introduced.

3. **Locale file completeness matters**: Creating `zh.json` with all keys (not just the ones listed in the task reference section) prevents console warnings about missing translation keys. The task reference section only listed a subset of keys.

### Documentation Impact

- **`docs/developer/ui-ux/i18n-patterns.md`**: Should mention the `i18n.t()` pattern explicitly for class components (not just "non-React contexts"), since `ErrorBoundary` is a React component that cannot use hooks.
- **CSS logical properties**: The task spec's audit table is a useful reference. Consider adding a brief note to `i18n-patterns.md` or a separate CSS/RTL doc about the logical property convention.
- **ast-grep rule opportunity**: A new static analysis rule could enforce CSS logical properties (`ps-`/`pe-`/`ms-`/`me-`/`text-start`/`text-end`) and flag physical equivalents, similar to the existing Zustand destructuring rule.
