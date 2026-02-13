import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CommandContext } from './types'

vi.mock('@/lib/quick-note/open-quick-note', () => ({
  openQuickNoteDialog: vi.fn(),
}))

const { noteCommands } = await import('./note-commands')
const { openQuickNoteDialog } = await import('@/lib/quick-note/open-quick-note')

const openQuickNoteDialogMock = vi.mocked(openQuickNoteDialog)

function createMockContext(): CommandContext {
  return {
    openPreferences: vi.fn(),
    showToast: vi.fn(),
  }
}

describe('noteCommands', () => {
  beforeEach(() => {
    openQuickNoteDialogMock.mockReset()
  })

  it('registers create-note command metadata', () => {
    const command = noteCommands.find(cmd => cmd.id === 'create-note')

    expect(command).toBeDefined()
    expect(command?.labelKey).toBe('commands.createNote.label')
    expect(command?.descriptionKey).toBe('commands.createNote.description')
    expect(command?.group).toBe('notes')
    expect(command?.shortcut).toBe('⌘+N')
  })

  it('opens the quick note dialog when executed', () => {
    const command = noteCommands.find(cmd => cmd.id === 'create-note')
    expect(command).toBeDefined()

    command?.execute(createMockContext())

    expect(openQuickNoteDialogMock).toHaveBeenCalledTimes(1)
  })
})
