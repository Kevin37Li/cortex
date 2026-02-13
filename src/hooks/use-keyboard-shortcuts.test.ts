import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useUIStore } from '@/store/ui-store'
import type { CommandContext } from '@/lib/commands/types'
import { useKeyboardShortcuts } from './use-keyboard-shortcuts'

function createCommandContext(): CommandContext {
  return {
    openPreferences: vi.fn(),
    showToast: vi.fn(),
  }
}

describe('useKeyboardShortcuts', () => {
  beforeEach(() => {
    useUIStore.setState({
      leftSidebarVisible: true,
      rightSidebarVisible: true,
      commandPaletteOpen: false,
      preferencesOpen: false,
      quickNoteDialogOpen: false,
      lastQuickPaneEntry: null,
    })
  })

  it('opens quick note dialog with Cmd+N', () => {
    renderHook(() => useKeyboardShortcuts(createCommandContext()))

    const event = new KeyboardEvent('keydown', {
      key: 'n',
      metaKey: true,
      cancelable: true,
    })
    document.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(true)
  })

  it('opens quick note dialog with Ctrl+N', () => {
    renderHook(() => useKeyboardShortcuts(createCommandContext()))

    const event = new KeyboardEvent('keydown', {
      key: 'n',
      ctrlKey: true,
      cancelable: true,
    })
    document.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(true)
  })

  it('prevents default and does not open quick note when command palette is open', () => {
    useUIStore.setState({
      commandPaletteOpen: true,
      preferencesOpen: false,
      quickNoteDialogOpen: false,
    })
    renderHook(() => useKeyboardShortcuts(createCommandContext()))

    const event = new KeyboardEvent('keydown', {
      key: 'n',
      metaKey: true,
      cancelable: true,
    })
    document.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(false)
  })

  it('prevents default and does not open quick note when preferences are open', () => {
    useUIStore.setState({
      commandPaletteOpen: false,
      preferencesOpen: true,
      quickNoteDialogOpen: false,
    })
    renderHook(() => useKeyboardShortcuts(createCommandContext()))

    const event = new KeyboardEvent('keydown', {
      key: 'n',
      metaKey: true,
      cancelable: true,
    })
    document.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(false)
  })

  it('prevents default when quick note dialog is already open', () => {
    useUIStore.setState({
      commandPaletteOpen: false,
      preferencesOpen: false,
      quickNoteDialogOpen: true,
    })
    renderHook(() => useKeyboardShortcuts(createCommandContext()))

    const event = new KeyboardEvent('keydown', {
      key: 'n',
      metaKey: true,
      cancelable: true,
    })
    document.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(true)
  })
})
