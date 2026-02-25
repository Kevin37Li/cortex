import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useUIStore } from '@/store/ui-store'
import type { CommandContext } from './types'
import { searchCommands } from './search-commands'

function createMockContext(): CommandContext {
  return {
    openPreferences: vi.fn(),
    showToast: vi.fn(),
  }
}

describe('searchCommands', () => {
  beforeEach(() => {
    useUIStore.setState({ searchFocused: false })
  })

  it('registers focus-search command metadata', () => {
    const command = searchCommands.find(cmd => cmd.id === 'focus-search')

    expect(command).toBeDefined()
    expect(command?.labelKey).toBe('commands.focusSearch.label')
    expect(command?.descriptionKey).toBe('commands.focusSearch.description')
    expect(command?.group).toBe('navigation')
    expect(command?.shortcut).toBe('⌘+F')
    expect(command?.keywords).toEqual(['search', 'find', 'query'])
  })

  it('sets searchFocused to true when executed', () => {
    const command = searchCommands.find(cmd => cmd.id === 'focus-search')
    expect(command).toBeDefined()

    command?.execute(createMockContext())

    expect(useUIStore.getState().searchFocused).toBe(true)
  })
})
