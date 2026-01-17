# Task: Verify and Complete Phase 1 Translation Keys

## Summary

Audit existing translation keys and add any missing strings for Phase 1 UI components.

## Acceptance Criteria

- [ ] All Phase 1 UI strings use translation keys (no hardcoded strings)
- [ ] Navigation labels added (`nav.allItems`, `nav.conversations`)
- [ ] Empty states translated
- [ ] Error messages translated
- [ ] Settings labels translated
- [ ] RTL-compatible CSS (logical properties) verified

## Dependencies

- Task 9: Frontend routing and navigation (for nav labels)

## Technical Notes

- Follow patterns in `docs/developer/ui-ux/i18n-patterns.md`
- Use `useTranslation` hook in React components
- Use `i18n.t()` in non-React code
- CSS should use `text-start`/`text-end` not `text-left`/`text-right`

## Audit Checklist

### Existing Components (verify keys exist)

- [ ] `CommandPalette.tsx` - uses `t('commandPalette.*')`
- [ ] `PreferencesDialog.tsx` - uses `t('preferences.*')`
- [ ] `TitleBar.tsx` - any visible text
- [ ] `ThemeProvider.tsx` - theme labels if any

### New Components (add keys)

- [ ] `LeftSideBar.tsx` navigation items
- [ ] Empty states for item list
- [ ] Loading states
- [ ] Error boundaries

## Translation Keys to Add

```json
{
  "nav": {
    "allItems": "All Items",
    "conversations": "Conversations",
    "settings": "Settings"
  },
  "items": {
    "empty": {
      "title": "No items yet",
      "description": "Save content from the web or create a note to get started."
    },
    "loading": "Loading items..."
  },
  "common": {
    "loading": "Loading...",
    "error": "Something went wrong",
    "retry": "Try again"
  }
}
```

## Files to Modify

- `locales/en.json` - Add missing keys
- `locales/ar.json` - Add translations (for RTL testing)
- `locales/fr.json` - Add translations

## Verification

1. Switch language in preferences
2. All UI text updates to new language
3. RTL layout works correctly with Arabic
4. No console warnings about missing translation keys
