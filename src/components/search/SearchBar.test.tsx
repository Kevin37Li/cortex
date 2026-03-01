import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@/test/test-utils'
import i18n from '@/i18n/config'
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'
import type { CommandContext } from '@/lib/commands/types'
import { useUIStore } from '@/store/ui-store'
import { SearchBar } from './SearchBar'

function createCommandContext(): CommandContext {
  return {
    openPreferences: vi.fn(),
    showToast: vi.fn(),
  }
}

function SearchFocusHarness() {
  const [value, setValue] = useState('')
  useKeyboardShortcuts(createCommandContext())

  return <SearchBar value={value} onValueChange={setValue} />
}

function ControlledSearchBarHarness() {
  const [value, setValue] = useState('graph')

  return <SearchBar value={value} onValueChange={setValue} />
}

describe('SearchBar', () => {
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

  it('renders controlled input and clear button', async () => {
    const onValueChange = vi.fn()

    render(<SearchBar value="graph" onValueChange={onValueChange} />)

    const input = await screen.findByRole('searchbox', {
      name: 'Search your knowledge base',
    })

    expect(input).toHaveValue('graph')

    fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))
    expect(onValueChange).toHaveBeenCalledWith('')
  })

  it('calls onValueChange when typing', async () => {
    const onValueChange = vi.fn()

    render(<SearchBar value="" onValueChange={onValueChange} />)

    const searchInput = await screen.findByRole('searchbox', {
      name: 'Search your knowledge base',
    })

    fireEvent.change(searchInput, {
      target: { value: 'knowledge graph' },
    })

    expect(onValueChange).toHaveBeenCalledWith('knowledge graph')
  })

  it('clears value and keeps input focused', async () => {
    render(<ControlledSearchBarHarness />)

    const searchInput = await screen.findByRole('searchbox', {
      name: 'Search your knowledge base',
    })
    expect(searchInput).toHaveValue('graph')

    fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))

    await waitFor(() => {
      expect(searchInput).toHaveValue('')
    })
    expect(searchInput).toHaveFocus()
  })

  it('focuses input and resets searchFocused when the flag is set', async () => {
    render(<SearchBar value="" onValueChange={vi.fn()} />)

    const searchInput = await screen.findByRole('searchbox', {
      name: 'Search your knowledge base',
    })
    expect(searchInput).not.toHaveFocus()

    act(() => {
      useUIStore.getState().setSearchFocused(true)
    })

    await waitFor(() => {
      expect(searchInput).toHaveFocus()
      expect(useUIStore.getState().searchFocused).toBe(false)
    })
  })

  it('focuses input from Cmd+F and resets searchFocused', async () => {
    render(<SearchFocusHarness />, { initialPath: '/items' })

    const searchInput = await screen.findByRole('searchbox', {
      name: 'Search your knowledge base',
    })

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
