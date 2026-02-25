import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nextProvider } from 'react-i18next'
import { act, render, screen, waitFor } from '@testing-library/react'
import type { ReactElement } from 'react'
import i18n from '@/i18n/config'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'
import type { CommandContext } from '@/lib/commands/types'
import { useUIStore } from '@/store/ui-store'
import { ItemsSearchInput } from './ItemsSearchInput'

function createCommandContext(): CommandContext {
  return {
    openPreferences: vi.fn(),
    showToast: vi.fn(),
  }
}

function SearchFocusHarness() {
  useKeyboardShortcuts(createCommandContext())
  return <ItemsSearchInput />
}

function renderWithI18n(ui: ReactElement) {
  return render(<I18nextProvider i18n={i18n}>{ui}</I18nextProvider>)
}

describe('ItemsSearchInput', () => {
  beforeEach(async () => {
    useUIStore.setState({
      leftSidebarVisible: true,
      rightSidebarVisible: true,
      commandPaletteOpen: false,
      preferencesOpen: false,
      quickNoteDialogOpen: false,
      searchFocused: false,
      lastQuickPaneEntry: null,
    })
    await i18n.changeLanguage('en')
  })

  it('focuses the input and resets searchFocused when the flag is set', async () => {
    renderWithI18n(<ItemsSearchInput />)

    const searchInput = screen.getByRole('searchbox', { name: 'Search items' })
    expect(searchInput).not.toHaveFocus()

    act(() => {
      useUIStore.getState().setSearchFocused(true)
    })

    await waitFor(() => {
      expect(searchInput).toHaveFocus()
      expect(useUIStore.getState().searchFocused).toBe(false)
    })
  })

  it('focuses the input from Cmd+F and resets searchFocused', async () => {
    renderWithI18n(<SearchFocusHarness />)

    const searchInput = screen.getByRole('searchbox', { name: 'Search items' })
    const event = new KeyboardEvent('keydown', {
      key: 'f',
      metaKey: true,
      cancelable: true,
    })
    act(() => {
      document.dispatchEvent(event)
    })

    expect(event.defaultPrevented).toBe(true)

    await waitFor(() => {
      expect(searchInput).toHaveFocus()
      expect(useUIStore.getState().searchFocused).toBe(false)
    })
  })
})
