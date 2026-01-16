# Task: Configure Command Palette for MVP Actions

## Summary
Set up the existing command palette (Cmd+K) with MVP-relevant commands.

## Acceptance Criteria
- [ ] Command palette opens with Cmd+K (macOS) / Ctrl+K (Windows/Linux)
- [ ] MVP commands registered:
  - "New Note" - Opens quick note creation
  - "Search" - Focuses search input
  - "Settings" - Opens preferences
  - "Toggle Theme" - Switches light/dark
  - Navigation commands for main sections
- [ ] Fuzzy search filtering of commands
- [ ] Keyboard navigation (up/down arrows, enter to select)
- [ ] Closes on Escape or click outside

## Dependencies
- Task 10: Frontend routing (for navigation commands)

## Technical Notes
- Existing command palette in `src/components/command-palette/`
- Register commands via a central registry pattern
- Consider cmdk library if not already using
- Commands should have descriptions and optional keyboard shortcuts

## Phase
Phase 1: Foundation
