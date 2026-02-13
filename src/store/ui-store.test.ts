import { describe, it, expect, beforeEach } from 'vitest'
import { useUIStore } from './ui-store'

describe('UIStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useUIStore.setState({
      leftSidebarVisible: true,
      rightSidebarVisible: true,
      commandPaletteOpen: false,
      preferencesOpen: false,
      quickNoteDialogOpen: false,
      lastQuickPaneEntry: null,
    })
  })

  it('has correct initial state', () => {
    const state = useUIStore.getState()
    expect(state.leftSidebarVisible).toBe(true)
    expect(state.rightSidebarVisible).toBe(true)
    expect(state.commandPaletteOpen).toBe(false)
    expect(state.preferencesOpen).toBe(false)
    expect(state.quickNoteDialogOpen).toBe(false)
    expect(state.lastQuickPaneEntry).toBeNull()
  })

  it('toggles left sidebar visibility', () => {
    const { toggleLeftSidebar } = useUIStore.getState()

    toggleLeftSidebar()
    expect(useUIStore.getState().leftSidebarVisible).toBe(false)

    toggleLeftSidebar()
    expect(useUIStore.getState().leftSidebarVisible).toBe(true)
  })

  it('sets left sidebar visibility directly', () => {
    const { setLeftSidebarVisible } = useUIStore.getState()

    setLeftSidebarVisible(false)
    expect(useUIStore.getState().leftSidebarVisible).toBe(false)

    setLeftSidebarVisible(true)
    expect(useUIStore.getState().leftSidebarVisible).toBe(true)
  })

  it('toggles preferences dialog', () => {
    const { togglePreferences } = useUIStore.getState()

    togglePreferences()
    expect(useUIStore.getState().preferencesOpen).toBe(true)

    togglePreferences()
    expect(useUIStore.getState().preferencesOpen).toBe(false)
  })

  it('toggles command palette', () => {
    const { toggleCommandPalette } = useUIStore.getState()

    toggleCommandPalette()
    expect(useUIStore.getState().commandPaletteOpen).toBe(true)

    toggleCommandPalette()
    expect(useUIStore.getState().commandPaletteOpen).toBe(false)
  })

  it('toggles quick note dialog', () => {
    const { toggleQuickNoteDialog } = useUIStore.getState()

    toggleQuickNoteDialog()
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(true)

    toggleQuickNoteDialog()
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(false)
  })

  it('sets quick note dialog open state directly', () => {
    const { setQuickNoteDialogOpen } = useUIStore.getState()

    setQuickNoteDialogOpen(true)
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(true)

    setQuickNoteDialogOpen(false)
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(false)
  })
})
