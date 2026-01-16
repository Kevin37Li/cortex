# Task: Create Preferences Dialog for MVP Settings

## Summary
Implement a preferences dialog with MVP-relevant settings sections.

## Acceptance Criteria
- [ ] Preferences dialog accessible from:
  - Command palette "Settings" command
  - Keyboard shortcut (Cmd+,)
  - Menu item if present
- [ ] Settings sections:
  - **Appearance**: Theme selection (light/dark/system)
  - **AI Provider**: Placeholder for Ollama/OpenAI config (Phase 2 implementation)
- [ ] Settings persist across app restarts
- [ ] Dialog follows shadcn/ui patterns
- [ ] Cancel discards changes, Save applies changes

## Dependencies
- Task 12: Theme system (for theme settings to work)

## Technical Notes
- Existing preferences component in `src/components/preferences/`
- Store settings via Tauri commands for OS-level persistence
- Use tabs or sidebar for section navigation
- Placeholder sections can show "Coming soon" for post-MVP features

## Phase
Phase 1: Foundation
