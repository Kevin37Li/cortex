import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@/test/test-utils'
import i18n from '@/i18n/config'
import type { Item, ItemListResponse } from '@/services/items'
import { ItemList } from './ItemList'

vi.mock('@/services/items', async () => {
  const actual = await vi.importActual('@/services/items')

  return {
    ...actual,
    useItems: vi.fn(),
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

const { useItems, useRetryProcessing } = await import('@/services/items')
const { toast } = await import('sonner')

type UseItemsResult = ReturnType<typeof useItems>
type UseRetryProcessingResult = ReturnType<typeof useRetryProcessing>

const useItemsMock = vi.mocked(useItems)
const useRetryProcessingMock = vi.mocked(useRetryProcessing)

function createItem(index: number): Item {
  return {
    id: `item-${index}`,
    title: `Item ${index}`,
    content: `Content ${index}`,
    content_type: index % 2 === 0 ? 'note' : 'webpage',
    source_url: null,
    created_at: '2026-02-12T10:00:00Z',
    updated_at: '2026-02-12T10:00:00Z',
    processing_status: index % 4 === 0 ? 'failed' : 'completed',
    metadata: null,
  }
}

function createListResponse({
  itemCount,
  total,
  limit,
  offset = 0,
}: {
  itemCount: number
  total: number
  limit: number
  offset?: number
}): ItemListResponse {
  return {
    items: Array.from({ length: itemCount }, (_, index) =>
      createItem(offset + index + 1)
    ),
    total,
    offset,
    limit,
  }
}

function createQueryResult(overrides: Partial<UseItemsResult>): UseItemsResult {
  return {
    data: undefined,
    error: null,
    isError: false,
    isPending: false,
    isFetching: false,
    isPlaceholderData: false,
    refetch: vi.fn(),
    ...overrides,
  } as UseItemsResult
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

describe('ItemList', () => {
  beforeEach(async () => {
    useItemsMock.mockReset()
    useRetryProcessingMock.mockReset()
    useRetryProcessingMock.mockReturnValue(createRetryMutationResult())
    vi.mocked(toast.success).mockReset()
    vi.mocked(toast.info).mockReset()
    vi.mocked(toast.warning).mockReset()
    vi.mocked(toast.error).mockReset()
    await i18n.changeLanguage('en')
  })

  it('renders loading skeleton state', async () => {
    useItemsMock.mockReturnValue(createQueryResult({ isPending: true }))

    render(<ItemList />)

    await waitFor(() => {
      expect(screen.getByText('Loading items...')).toBeInTheDocument()
    })
  })

  it('renders empty state', async () => {
    useItemsMock.mockReturnValue(
      createQueryResult({
        data: createListResponse({
          itemCount: 0,
          total: 0,
          limit: 20,
        }),
      })
    )

    render(<ItemList />)

    await waitFor(() => {
      expect(screen.getByText('No items yet')).toBeInTheDocument()
    })
    expect(
      screen.getByText('Create a note or save a web page to get started')
    ).toBeInTheDocument()
  })

  it('renders error state with retry action', async () => {
    const refetch = vi.fn()
    useItemsMock.mockReturnValue(
      createQueryResult({
        isError: true,
        error: new Error('Failed to load'),
        refetch,
      })
    )

    render(<ItemList />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(refetch).toHaveBeenCalledTimes(1)
  })

  it('shows pagination when total exceeds page size', async () => {
    useItemsMock.mockImplementation(params => {
      const offset = params?.offset ?? 0
      const limit = params?.limit ?? 20

      return createQueryResult({
        data: createListResponse({
          itemCount: limit,
          total: 45,
          limit,
          offset,
        }),
      })
    })

    render(<ItemList pageSize={20} />, { initialPath: '/items' })

    await waitFor(() => {
      expect(useItemsMock).toHaveBeenLastCalledWith(
        { offset: 0, limit: 20 },
        expect.any(Object)
      )
    })

    // Should show pagination nav and page indicator
    expect(
      screen.getByRole('navigation', { name: 'pagination' })
    ).toBeInTheDocument()
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
  })

  it('navigates to next page with correct offset', async () => {
    useItemsMock.mockImplementation(params => {
      const offset = params?.offset ?? 0
      const limit = params?.limit ?? 20
      const total = 45
      const itemCount = Math.min(limit, total - offset)

      return createQueryResult({
        data: createListResponse({
          itemCount,
          total,
          limit,
          offset,
        }),
      })
    })

    render(<ItemList pageSize={20} />, { initialPath: '/items' })

    await waitFor(() => {
      expect(useItemsMock).toHaveBeenLastCalledWith(
        { offset: 0, limit: 20 },
        expect.any(Object)
      )
    })

    fireEvent.click(screen.getByRole('button', { name: 'Go to next page' }))

    await waitFor(() => {
      expect(useItemsMock).toHaveBeenLastCalledWith(
        { offset: 20, limit: 20 },
        expect.any(Object)
      )
    })
    expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
  })

  it('navigates to previous page with correct offset', async () => {
    useItemsMock.mockImplementation(params => {
      const offset = params?.offset ?? 0
      const limit = params?.limit ?? 20
      const total = 45
      const itemCount = Math.min(limit, total - offset)

      return createQueryResult({
        data: createListResponse({
          itemCount,
          total,
          limit,
          offset,
        }),
      })
    })

    render(<ItemList pageSize={20} />, { initialPath: '/items' })

    // Wait for initial render
    await waitFor(() => {
      expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
    })

    // Navigate to page 2 first
    fireEvent.click(screen.getByRole('button', { name: 'Go to next page' }))

    await waitFor(() => {
      expect(useItemsMock).toHaveBeenLastCalledWith(
        { offset: 20, limit: 20 },
        expect.any(Object)
      )
    })

    // Navigate back to page 1
    fireEvent.click(screen.getByRole('button', { name: 'Go to previous page' }))

    await waitFor(() => {
      expect(useItemsMock).toHaveBeenLastCalledWith(
        { offset: 0, limit: 20 },
        expect.any(Object)
      )
    })
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
  })

  it('disables previous button on first page', async () => {
    useItemsMock.mockReturnValue(
      createQueryResult({
        data: createListResponse({
          itemCount: 20,
          total: 45,
          limit: 20,
          offset: 0,
        }),
      })
    )

    render(<ItemList pageSize={20} />, { initialPath: '/items' })

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Go to previous page' })
      ).toBeDisabled()
    })
    expect(
      screen.getByRole('button', { name: 'Go to next page' })
    ).not.toBeDisabled()
  })

  it('disables next button on last page', async () => {
    useItemsMock.mockImplementation(params => {
      const offset = params?.offset ?? 0
      const limit = params?.limit ?? 20
      const total = 45
      const itemCount = Math.min(limit, total - offset)

      return createQueryResult({
        data: createListResponse({
          itemCount,
          total,
          limit,
          offset,
        }),
      })
    })

    render(<ItemList pageSize={20} />, { initialPath: '/items' })

    // Wait for initial render
    await waitFor(() => {
      expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
    })

    // Navigate to page 3 (last page)
    fireEvent.click(screen.getByRole('button', { name: 'Go to next page' }))
    fireEvent.click(screen.getByRole('button', { name: 'Go to next page' }))

    await waitFor(() => {
      expect(screen.getByText('Page 3 of 3')).toBeInTheDocument()
    })

    expect(
      screen.getByRole('button', { name: 'Go to next page' })
    ).toBeDisabled()
    expect(
      screen.getByRole('button', { name: 'Go to previous page' })
    ).not.toBeDisabled()
  })

  it('hides pagination when all items fit one page', async () => {
    useItemsMock.mockReturnValue(
      createQueryResult({
        data: createListResponse({
          itemCount: 10,
          total: 10,
          limit: 20,
          offset: 0,
        }),
      })
    )

    render(<ItemList pageSize={20} />, { initialPath: '/items' })

    await waitFor(() => {
      expect(screen.getAllByRole('link')).toHaveLength(10)
    })

    expect(
      screen.queryByRole('navigation', { name: 'pagination' })
    ).not.toBeInTheDocument()
  })

  it('can navigate beyond 100 items with no hard cap', async () => {
    const total = 250

    useItemsMock.mockImplementation(params => {
      const offset = params?.offset ?? 0
      const limit = params?.limit ?? 20
      const itemCount = Math.min(limit, total - offset)

      return createQueryResult({
        data: createListResponse({
          itemCount,
          total,
          limit,
          offset,
        }),
      })
    })

    render(<ItemList pageSize={20} />, { initialPath: '/items' })

    await waitFor(() => {
      expect(screen.getByText('Page 1 of 13')).toBeInTheDocument()
    })

    // Click page 7 (offset = 120, beyond the old 100 cap)
    fireEvent.click(screen.getByRole('button', { name: '13' }))

    await waitFor(() => {
      expect(useItemsMock).toHaveBeenLastCalledWith(
        { offset: 240, limit: 20 },
        expect.any(Object)
      )
    })
    expect(screen.getByText('Page 13 of 13')).toBeInTheDocument()
  })

  it('clamps current page when total pages shrink', async () => {
    let hasShrunk = false

    useItemsMock.mockImplementation(params => {
      const offset = params?.offset ?? 0
      const limit = params?.limit ?? 20
      const total = hasShrunk ? 20 : 45
      const itemCount = Math.max(0, Math.min(limit, total - offset))

      return createQueryResult({
        data: createListResponse({
          itemCount,
          total,
          limit,
          offset,
        }),
      })
    })

    const { rerender } = render(<ItemList pageSize={20} />, {
      initialPath: '/items',
    })

    await waitFor(() => {
      expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Go to next page' }))
    fireEvent.click(screen.getByRole('button', { name: 'Go to next page' }))

    await waitFor(() => {
      expect(screen.getByText('Page 3 of 3')).toBeInTheDocument()
      expect(useItemsMock).toHaveBeenLastCalledWith(
        { offset: 40, limit: 20 },
        expect.any(Object)
      )
    })

    hasShrunk = true
    rerender(<ItemList pageSize={20} />)

    await waitFor(() => {
      expect(useItemsMock).toHaveBeenLastCalledWith(
        { offset: 0, limit: 20 },
        expect.any(Object)
      )
    })
    expect(screen.queryByText('Page 3 of 3')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('navigation', { name: 'pagination' })
    ).not.toBeInTheDocument()
  })

  it('retries a failed item from the list and shows success feedback', async () => {
    const failedItem = createItem(4)
    const mutateAsync = vi.fn().mockResolvedValue({
      retried_count: 1,
      outcome: 'retried',
    })
    useRetryProcessingMock.mockReturnValue(
      createRetryMutationResult({ mutateAsync })
    )
    useItemsMock.mockReturnValue(
      createQueryResult({
        data: {
          items: [failedItem],
          total: 1,
          offset: 0,
          limit: 20,
        },
      })
    )

    render(<ItemList />, { initialPath: '/items' })

    fireEvent.click(
      await screen.findByRole('button', { name: 'Retry Processing' })
    )

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(failedItem.id)
    })
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith('Retry queued')
  })

  it('prevents duplicate retries for the same item while request is pending', async () => {
    const failedItem = createItem(8)
    let resolveRetry:
      | ((value: { retried_count: number; outcome: 'retried' }) => void)
      | undefined
    const mutateAsync = vi.fn(
      () =>
        new Promise<{ retried_count: number; outcome: 'retried' }>(resolve => {
          resolveRetry = resolve
        })
    )
    useRetryProcessingMock.mockReturnValue(
      createRetryMutationResult({ mutateAsync })
    )
    useItemsMock.mockReturnValue(
      createQueryResult({
        data: {
          items: [failedItem],
          total: 1,
          offset: 0,
          limit: 20,
        },
      })
    )

    render(<ItemList />, { initialPath: '/items' })

    const retryButton = await screen.findByRole('button', {
      name: 'Retry Processing',
    })
    fireEvent.click(retryButton)
    fireEvent.click(retryButton)

    expect(mutateAsync).toHaveBeenCalledTimes(1)

    resolveRetry?.({ retried_count: 1, outcome: 'retried' })

    await waitFor(() => {
      expect(vi.mocked(toast.success)).toHaveBeenCalledWith('Retry queued')
    })
  })

  it('renders localized pagination accessibility labels in Chinese', async () => {
    await i18n.changeLanguage('zh')

    useItemsMock.mockReturnValue(
      createQueryResult({
        data: createListResponse({
          itemCount: 20,
          total: 45,
          limit: 20,
          offset: 0,
        }),
      })
    )

    render(<ItemList pageSize={20} />, { initialPath: '/items' })

    await waitFor(() => {
      expect(
        screen.getByRole('navigation', { name: '分页' })
      ).toBeInTheDocument()
    })

    expect(
      screen.getByRole('button', { name: '转到上一页' })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: '转到下一页' })
    ).toBeInTheDocument()
    expect(screen.getByText('第 1 页，共 3 页')).toBeInTheDocument()
  })
})
