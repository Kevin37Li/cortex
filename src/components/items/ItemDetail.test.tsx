import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@/test/test-utils'
import i18n from '@/i18n/config'
import { ApiRequestError } from '@/lib/api-config'
import type { Item } from '@/services/items'
import { ItemDetail } from './ItemDetail'

vi.mock('@/services/items', async () => {
  const actual = await vi.importActual('@/services/items')

  return {
    ...actual,
    useItem: vi.fn(),
    useRetryProcessing: vi.fn(),
  }
})

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
  },
}))

const { useItem, useRetryProcessing } = await import('@/services/items')
const { openUrl } = await import('@tauri-apps/plugin-opener')
const { toast } = await import('sonner')

type UseItemResult = ReturnType<typeof useItem>
type UseRetryProcessingResult = ReturnType<typeof useRetryProcessing>

const useItemMock = vi.mocked(useItem)
const useRetryProcessingMock = vi.mocked(useRetryProcessing)
const openUrlMock = vi.mocked(openUrl)

const baseItem: Item = {
  id: 'item-1',
  title: 'Research Notes',
  content: 'Line one\nLine two',
  content_type: 'note',
  source_url: 'https://example.com/source',
  created_at: '2026-02-14T08:30:00Z',
  updated_at: '2026-02-14T08:30:00Z',
  processing_status: 'completed',
  metadata: {
    summary: 'Short summary',
    concepts: ['Knowledge Graph'],
    entities: ['Cortex'],
  },
}

function createItemQueryResult(
  overrides: Partial<UseItemResult>
): UseItemResult {
  return {
    data: undefined,
    error: null,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
    ...overrides,
  } as UseItemResult
}

function createRetryMutationResult(
  overrides: Partial<UseRetryProcessingResult> = {}
): UseRetryProcessingResult {
  return {
    mutateAsync: vi.fn(),
    isPending: false,
    ...overrides,
  } as UseRetryProcessingResult
}

describe('ItemDetail', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage('en')
  })

  it('renders loading skeleton state', async () => {
    useItemMock.mockReturnValue(createItemQueryResult({ isPending: true }))
    useRetryProcessingMock.mockReturnValue(createRetryMutationResult())

    render(<ItemDetail itemId={baseItem.id} />, {
      initialPath: `/items/${baseItem.id}`,
    })

    await waitFor(() => {
      expect(screen.getByText('Loading item details...')).toBeInTheDocument()
    })
  })

  it('renders dedicated not-found state', async () => {
    useItemMock.mockReturnValue(
      createItemQueryResult({
        isError: true,
        error: new ApiRequestError({
          message: `Item not found: ${baseItem.id}`,
          status: 404,
          path: `/api/items/${baseItem.id}`,
          code: 'item_not_found',
        }),
      })
    )
    useRetryProcessingMock.mockReturnValue(createRetryMutationResult())

    render(<ItemDetail itemId={baseItem.id} />, {
      initialPath: `/items/${baseItem.id}`,
    })

    await waitFor(() => {
      expect(screen.getByText('Item not found')).toBeInTheDocument()
    })
    expect(
      screen.getByText('This item may have been deleted')
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Items' })).toHaveAttribute(
      'href',
      '/items'
    )
  })

  it('renders generic error state with retry refetch action', async () => {
    const refetch = vi.fn()
    useItemMock.mockReturnValue(
      createItemQueryResult({
        isError: true,
        error: new Error('API request failed (500)'),
        refetch,
      })
    )
    useRetryProcessingMock.mockReturnValue(createRetryMutationResult())

    render(<ItemDetail itemId={baseItem.id} />, {
      initialPath: `/items/${baseItem.id}`,
    })

    await waitFor(() => {
      expect(screen.getByText('Failed to load item')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(refetch).toHaveBeenCalledTimes(1)
  })

  it('renders item content, metadata, and opens source URL', async () => {
    useItemMock.mockReturnValue(
      createItemQueryResult({
        data: baseItem,
      })
    )
    useRetryProcessingMock.mockReturnValue(createRetryMutationResult())

    render(<ItemDetail itemId={baseItem.id} />, {
      initialPath: `/items/${baseItem.id}`,
    })

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Research Notes' })
      ).toBeInTheDocument()
    })

    expect(screen.getByText('Note')).toBeInTheDocument()
    expect(screen.getByText(/Created:/)).toBeInTheDocument()

    const content = screen.getByText(/Line one\s+Line two/)
    expect(content).toHaveClass('whitespace-pre-wrap')

    expect(screen.getByText('Extracted Metadata')).toBeInTheDocument()
    expect(screen.getByText('Short summary')).toBeInTheDocument()
    expect(screen.getByText('Knowledge Graph')).toBeInTheDocument()
    expect(screen.getByText('Cortex')).toBeInTheDocument()

    fireEvent.click(
      screen.getByRole('button', { name: /https:\/\/example.com\/source/i })
    )
    expect(openUrlMock).toHaveBeenCalledWith('https://example.com/source')
  })

  it('shows failed processing details from metadata', async () => {
    const failedItem: Item = {
      ...baseItem,
      processing_status: 'failed',
      metadata: {
        processing_error: 'Embedding failed due to timeout',
        error_step: 'validating',
      },
    }

    useItemMock.mockReturnValue(createItemQueryResult({ data: failedItem }))
    useRetryProcessingMock.mockReturnValue(createRetryMutationResult())

    render(<ItemDetail itemId={failedItem.id} />, {
      initialPath: `/items/${failedItem.id}`,
    })

    await waitFor(() => {
      expect(screen.getByText('Failed')).toBeInTheDocument()
    })

    expect(screen.getByText('Processing failed')).toBeInTheDocument()
    expect(screen.getByText(/Failed step.*validating/i)).toBeInTheDocument()
    expect(
      screen.getByText('Embedding failed due to timeout')
    ).toBeInTheDocument()
    expect(screen.queryByText('Extracted Metadata')).not.toBeInTheDocument()
  })

  it('shows error toast when openUrl fails', async () => {
    openUrlMock.mockRejectedValueOnce(new Error('Permission denied'))
    useItemMock.mockReturnValue(createItemQueryResult({ data: baseItem }))
    useRetryProcessingMock.mockReturnValue(createRetryMutationResult())

    render(<ItemDetail itemId={baseItem.id} />, {
      initialPath: `/items/${baseItem.id}`,
    })

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /https:\/\/example.com\/source/i })
      ).toBeInTheDocument()
    })

    fireEvent.click(
      screen.getByRole('button', { name: /https:\/\/example.com\/source/i })
    )

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        'Failed to open source URL'
      )
    })
  })

  it('does not render source section when source_url is null', async () => {
    const noSourceItem: Item = { ...baseItem, source_url: null }
    useItemMock.mockReturnValue(createItemQueryResult({ data: noSourceItem }))
    useRetryProcessingMock.mockReturnValue(createRetryMutationResult())

    render(<ItemDetail itemId={noSourceItem.id} />, {
      initialPath: `/items/${noSourceItem.id}`,
    })

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Research Notes' })
      ).toBeInTheDocument()
    })

    expect(screen.queryByText('Source')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /https:\/\//i })
    ).not.toBeInTheDocument()
  })

  it.each([
    ['retried', 'success', 'Retry queued'],
    ['already_queued', 'info', 'Item is already queued for processing'],
    ['not_in_queue', 'warning', 'Item is not currently retryable'],
  ] as const)(
    'handles %s retry outcome with user feedback',
    async (outcome, toastMethod, message) => {
      const failedItem: Item = {
        ...baseItem,
        processing_status: 'failed',
      }
      const mutateAsync = vi.fn().mockResolvedValue({
        retried_count: outcome === 'retried' ? 1 : 0,
        outcome,
      })

      useItemMock.mockReturnValue(createItemQueryResult({ data: failedItem }))
      useRetryProcessingMock.mockReturnValue(
        createRetryMutationResult({ mutateAsync })
      )

      render(<ItemDetail itemId={failedItem.id} />, {
        initialPath: `/items/${failedItem.id}`,
      })

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: 'Retry Processing' })
        ).toBeInTheDocument()
      })

      fireEvent.click(screen.getByRole('button', { name: 'Retry Processing' }))

      await waitFor(() => {
        expect(mutateAsync).toHaveBeenCalledWith(failedItem.id)
      })
      expect(vi.mocked(toast[toastMethod])).toHaveBeenCalledWith(message)
    }
  )

  it('shows pending retry state as disabled button with retrying label', async () => {
    const failedItem: Item = {
      ...baseItem,
      processing_status: 'failed',
    }

    useItemMock.mockReturnValue(createItemQueryResult({ data: failedItem }))
    useRetryProcessingMock.mockReturnValue(
      createRetryMutationResult({
        isPending: true,
      })
    )

    render(<ItemDetail itemId={failedItem.id} />, {
      initialPath: `/items/${failedItem.id}`,
    })

    const retryingButton = await screen.findByRole('button', {
      name: 'Retrying...',
    })

    expect(retryingButton).toBeDisabled()
  })

  it('shows generic error toast when retry mutation fails', async () => {
    const failedItem: Item = {
      ...baseItem,
      processing_status: 'failed',
    }

    const mutateAsync = vi.fn().mockRejectedValue(new Error('Retry failed'))
    useItemMock.mockReturnValue(createItemQueryResult({ data: failedItem }))
    useRetryProcessingMock.mockReturnValue(
      createRetryMutationResult({ mutateAsync })
    )

    render(<ItemDetail itemId={failedItem.id} />, {
      initialPath: `/items/${failedItem.id}`,
    })

    fireEvent.click(
      await screen.findByRole('button', { name: 'Retry Processing' })
    )

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
        'Something went wrong'
      )
    })
  })
})
