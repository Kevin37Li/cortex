import { useEffect } from 'react'
import { useUIStore } from '@/store/ui-store'
import { openQuickNoteDialog } from '@/lib/quick-note/open-quick-note'
import type { CommandContext } from '@/lib/commands/types'

/**
 * Handles global keyboard shortcuts for the application.
 *
 * Currently handles:
 * - Cmd/Ctrl+, : Open preferences
 * - Cmd/Ctrl+N : Open quick note dialog
 * - Cmd/Ctrl+1 : Toggle left sidebar
 * - Cmd/Ctrl+2 : Toggle right sidebar
 */
export function useKeyboardShortcuts(commandContext: CommandContext) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey) {
        const { commandPaletteOpen, preferencesOpen, quickNoteDialogOpen } =
          useUIStore.getState()

        switch (e.key.toLowerCase()) {
          case ',': {
            e.preventDefault()
            commandContext.openPreferences()
            break
          }
          case 'n': {
            e.preventDefault()
            if (commandPaletteOpen || preferencesOpen || quickNoteDialogOpen) {
              break
            }
            openQuickNoteDialog()
            break
          }
          case '1': {
            e.preventDefault()
            const { leftSidebarVisible, setLeftSidebarVisible } =
              useUIStore.getState()
            setLeftSidebarVisible(!leftSidebarVisible)
            break
          }
          case '2': {
            e.preventDefault()
            const { rightSidebarVisible, setRightSidebarVisible } =
              useUIStore.getState()
            setRightSidebarVisible(!rightSidebarVisible)
            break
          }
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [commandContext])
}
