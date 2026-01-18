# Task: Implement Basic Routing and Navigation

## Summary

Add client-side routing to the frontend to support navigation between main views (All Items, Conversations) and proper URL-based state.

## Acceptance Criteria

- [ ] Router setup using `@tanstack/react-router` or similar
- [ ] Routes defined:
  - `/` - Redirect to `/items`
  - `/items` - All items list view
  - `/items/:id` - Single item detail view
  - `/conversations` - Conversations list
  - `/conversations/:id` - Single conversation
  - `/settings` - Settings page (or use existing dialog)
- [ ] Left sidebar shows navigation links
- [ ] Active route highlighted in sidebar
- [ ] Browser back/forward navigation works
- [ ] Deep linking works (paste URL, get correct view)

## Dependencies

- None (frontend shell already exists)

## Technical Notes

- Use `@tanstack/react-router` for type-safe routing
- Tauri apps use hash-based routing (`/#/items`) for file:// compatibility
- Navigation state can coexist with Zustand UI state
- Keep existing command palette and preferences dialog as overlays

## Left Sidebar Navigation

```tsx
// Navigation items for sidebar
const navItems = [
  { path: '/items', labelKey: 'nav.allItems', icon: FileTextIcon },
  {
    path: '/conversations',
    labelKey: 'nav.conversations',
    icon: MessageSquareIcon,
  },
]
```

## Files to Create/Modify

- `src/lib/router.ts` - Router configuration
- `src/routes/` - Route components
  - `src/routes/items.tsx` - Items list
  - `src/routes/item-detail.tsx` - Single item
  - `src/routes/conversations.tsx` - Conversations list
  - `src/routes/conversation.tsx` - Single conversation
- `src/components/layout/LeftSideBar.tsx` - Add navigation
- `src/main.tsx` - Add RouterProvider
- `locales/en.json` - Add navigation translation keys

## Verification

1. Navigate between routes using sidebar
2. Click back button returns to previous route
3. Refresh page maintains current route
4. Command palette still works from any route
5. Preferences dialog still works from any route
