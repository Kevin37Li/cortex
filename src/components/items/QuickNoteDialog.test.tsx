import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@/test/test-utils'
import i18n from '@/i18n/config'
import { useUIStore } from '@/store/ui-store'
import { QuickNoteDialog } from './QuickNoteDialog'

vi.mock('@/services/items', async () => {
  const actual = await vi.importActual('@/services/items')

  return {
    ...actual,
    useCreateItem: vi.fn(),
  }
})

vi.mock('@/lib/notifications', () => ({
  notifications: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

const { useCreateItem } = await import('@/services/items')
const { notifications } = await import('@/lib/notifications')

const useCreateItemMock = vi.mocked(useCreateItem)
const successMock = vi.mocked(notifications.success)
const errorMock = vi.mocked(notifications.error)

const mutateAsync = vi.fn()

async function renderOpenDialog() {
  render(<QuickNoteDialog />)
  act(() => {
    useUIStore.getState().setQuickNoteDialogOpen(true)
  })
  await screen.findByText('New Note')
}

describe('QuickNoteDialog', () => {
  beforeEach(async () => {
    mutateAsync.mockReset()
    successMock.mockReset()
    errorMock.mockReset()

    useUIStore.setState({
      leftSidebarVisible: true,
      rightSidebarVisible: true,
      commandPaletteOpen: false,
      preferencesOpen: false,
      quickNoteDialogOpen: false,
      lastQuickPaneEntry: null,
    })

    useCreateItemMock.mockReturnValue({
      mutateAsync,
    } as unknown as ReturnType<typeof useCreateItem>)

    await i18n.changeLanguage('en')
  })

  it('submits a note with the expected payload and closes on success', async () => {
    mutateAsync.mockResolvedValue({
      id: 'note-1',
      title: 'My note',
      content: 'Markdown content',
      content_type: 'note',
      source_url: null,
      created_at: '2026-02-13T10:00:00Z',
      updated_at: '2026-02-13T10:00:00Z',
      processing_status: 'completed',
      metadata: null,
    })

    await renderOpenDialog()

    fireEvent.change(screen.getByLabelText('Title'), {
      target: { value: '  My note  ' },
    })
    fireEvent.change(screen.getByLabelText('Content'), {
      target: { value: '  Markdown content  ' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save Note' }))

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        title: 'My note',
        content: 'Markdown content',
        content_type: 'note',
      })
    })
    await waitFor(() => {
      expect(successMock).toHaveBeenCalledWith('Note saved')
    })
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(false)
  })

  it('shows required-field validation errors and blocks submission', async () => {
    await renderOpenDialog()

    fireEvent.click(screen.getByRole('button', { name: 'Save Note' }))

    await waitFor(() => {
      expect(screen.getByText('Title is required')).toBeInTheDocument()
      expect(screen.getByText('Content is required')).toBeInTheDocument()
    })
    expect(mutateAsync).not.toHaveBeenCalled()
  })

  it('shows an error notification and preserves the form on failure', async () => {
    mutateAsync.mockRejectedValue(new Error('Request failed'))

    await renderOpenDialog()

    fireEvent.change(screen.getByLabelText('Title'), {
      target: { value: 'Retry title' },
    })
    fireEvent.change(screen.getByLabelText('Content'), {
      target: { value: 'Retry content' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save Note' }))

    await waitFor(() => {
      expect(errorMock).toHaveBeenCalledWith('Failed to save note')
    })
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(true)
    expect(screen.getByLabelText('Title')).toHaveValue('Retry title')
    expect(screen.getByLabelText('Content')).toHaveValue('Retry content')
  })

  it('disables submit and shows spinner while saving', async () => {
    let resolveMutation: (() => void) | undefined

    mutateAsync.mockReturnValue(
      new Promise(resolve => {
        resolveMutation = () => resolve(undefined)
      })
    )

    await renderOpenDialog()

    fireEvent.change(screen.getByLabelText('Title'), {
      target: { value: 'Pending title' },
    })
    fireEvent.change(screen.getByLabelText('Content'), {
      target: { value: 'Pending content' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save Note' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Saving...' })).toBeDisabled()
      expect(
        screen.getByTestId('quick-note-saving-spinner')
      ).toBeInTheDocument()
    })

    await act(async () => {
      resolveMutation?.()
    })

    await waitFor(() => {
      expect(successMock).toHaveBeenCalledWith('Note saved')
    })
  })

  it('resets form values when the dialog closes', async () => {
    await renderOpenDialog()

    fireEvent.change(screen.getByLabelText('Title'), {
      target: { value: 'Temporary title' },
    })
    fireEvent.change(screen.getByLabelText('Content'), {
      target: { value: 'Temporary content' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(useUIStore.getState().quickNoteDialogOpen).toBe(false)

    act(() => {
      useUIStore.getState().setQuickNoteDialogOpen(true)
    })

    await waitFor(() => {
      expect(screen.getByLabelText('Title')).toHaveValue('')
      expect(screen.getByLabelText('Content')).toHaveValue('')
    })
  })
})
