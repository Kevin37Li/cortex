import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Item, ItemCreate, ItemUpdate } from './items'

vi.mock('@/lib/logger', () => ({
  logger: {
    trace: vi.fn(),
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}))

const { API_BASE } = await import('@/lib/api-config')
const { logger } = await import('@/lib/logger')
const {
  createItem,
  itemQueryKeys,
  useCreateItem,
  useDeleteItem,
  useItem,
  useItems,
  useUpdateItem,
} = await import('./items')

const fetchMock = vi.fn()

const sampleItem: Item = {
  id: 'item-1',
  title: 'Sample Item',
  content: 'Sample content',
  content_type: 'note',
  source_url: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  processing_status: 'pending',
  metadata: null,
}
const specialItemId = 'item/with spaces?#'

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function createWrapper(queryClient: QueryClient) {
  function TestQueryClientProvider({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }

  TestQueryClientProvider.displayName = 'TestQueryClientProvider'

  return TestQueryClientProvider
}

function createMockResponse({
  ok,
  status = 200,
  body,
  json,
}: {
  ok?: boolean
  status?: number
  body?: unknown
  json?: () => Promise<unknown>
}): Response {
  return {
    ok: ok ?? (status >= 200 && status < 300),
    status,
    json: json ?? vi.fn().mockResolvedValue(body),
    headers: new Headers(),
  } as Response
}

describe('itemQueryKeys', () => {
  it('creates expected query keys', () => {
    expect(itemQueryKeys.all).toEqual(['items'])
    expect(itemQueryKeys.lists()).toEqual(['items', 'list'])
    expect(itemQueryKeys.list({ offset: 0, limit: 25 })).toEqual([
      'items',
      'list',
      { offset: 0, limit: 25 },
    ])
    expect(itemQueryKeys.details()).toEqual(['items', 'detail'])
    expect(itemQueryKeys.detail('item-1')).toEqual([
      'items',
      'detail',
      'item-1',
    ])
  })
})

describe('item services', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  it('builds list request URL without query string when no params', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({
        body: {
          items: [sampleItem],
          total: 1,
          offset: 0,
          limit: 20,
        },
      })
    )

    const queryClient = createTestQueryClient()
    const { result } = renderHook(() => useItems(), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(`${API_BASE}/api/items/`)
  })

  it('builds list request URL with pagination params', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({
        body: {
          items: [sampleItem],
          total: 1,
          offset: 0,
          limit: 25,
        },
      })
    )

    const queryClient = createTestQueryClient()
    const { result } = renderHook(() => useItems({ offset: 0, limit: 25 }), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(`${API_BASE}/api/items/?offset=0&limit=25`)
  })

  it('builds detail request URL with encoded id', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({ body: { ...sampleItem, id: specialItemId } })
    )

    const queryClient = createTestQueryClient()
    const { result } = renderHook(() => useItem(specialItemId), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(
      `${API_BASE}/api/items/${encodeURIComponent(specialItemId)}`
    )
  })

  it('creates an item via non-hook createItem service', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({ status: 201, body: sampleItem })
    )

    const createPayload: ItemCreate = {
      title: 'Imported file',
      content: '# Hello',
      content_type: 'file',
      source_url: null,
      metadata: null,
    }

    const created = await createItem(createPayload)

    expect(created).toEqual(sampleItem)
    const [url, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${API_BASE}/api/items/`)
    expect(requestInit.method).toBe('POST')
    expect(requestInit.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(requestInit.body).toBe(JSON.stringify(createPayload))
  })

  it('invalidates list queries after create mutation', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({ status: 201, body: sampleItem })
    )

    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const wrapper = createWrapper(queryClient)

    const createPayload: ItemCreate = {
      title: 'New item',
      content: 'New content',
      content_type: 'note',
      source_url: null,
      metadata: null,
    }

    const { result } = renderHook(() => useCreateItem(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync(createPayload)
    })

    const [url, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${API_BASE}/api/items/`)
    expect(requestInit.method).toBe('POST')
    expect(requestInit.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(requestInit.body).toBe(JSON.stringify(createPayload))
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: itemQueryKeys.lists(),
    })
  })

  it('invalidates list and detail queries after update mutation', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({
        body: { ...sampleItem, title: 'Updated title' },
      })
    )

    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const wrapper = createWrapper(queryClient)

    const updatePayload: ItemUpdate = { title: 'Updated title' }
    const { result } = renderHook(() => useUpdateItem(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync({
        id: specialItemId,
        data: updatePayload,
      })
    })

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(
      `${API_BASE}/api/items/${encodeURIComponent(specialItemId)}`
    )
    expect(invalidateSpy).toHaveBeenNthCalledWith(1, {
      queryKey: itemQueryKeys.lists(),
    })
    expect(invalidateSpy).toHaveBeenNthCalledWith(2, {
      queryKey: itemQueryKeys.detail(specialItemId),
    })
  })

  it('handles structured backend errors and propagates message', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({
        status: 404,
        body: {
          error: 'item_not_found',
          message: `Item not found: ${sampleItem.id}`,
        },
      })
    )

    const queryClient = createTestQueryClient()
    const { result } = renderHook(() => useItem(sampleItem.id), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    expect((result.current.error as Error).message).toBe(
      `Item not found: ${sampleItem.id}`
    )
    expect(logger.error).toHaveBeenCalledWith(
      'API request failed',
      expect.objectContaining({
        path: `/api/items/${sampleItem.id}`,
        status: 404,
        error: 'item_not_found',
        message: `Item not found: ${sampleItem.id}`,
      })
    )
  })

  it('handles FastAPI detail array errors and propagates merged message', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({
        status: 422,
        body: {
          detail: [{ msg: 'offset must be greater than or equal to 0' }],
        },
      })
    )

    const queryClient = createTestQueryClient()
    const { result } = renderHook(() => useItem(sampleItem.id), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    expect((result.current.error as Error).message).toBe(
      'offset must be greater than or equal to 0'
    )
    expect(logger.error).toHaveBeenCalledWith(
      'API request failed',
      expect.objectContaining({
        path: `/api/items/${sampleItem.id}`,
        status: 422,
        message: 'offset must be greater than or equal to 0',
      })
    )
  })

  it('does not parse JSON on delete 204 and clears detail cache', async () => {
    const jsonSpy = vi
      .fn<() => Promise<unknown>>()
      .mockRejectedValue(new Error('json should not be called'))

    fetchMock.mockResolvedValue(
      createMockResponse({
        status: 204,
        json: jsonSpy,
      })
    )

    const queryClient = createTestQueryClient()
    queryClient.setQueryData(itemQueryKeys.detail(specialItemId), {
      ...sampleItem,
      id: specialItemId,
    })

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const removeSpy = vi.spyOn(queryClient, 'removeQueries')
    const { result } = renderHook(() => useDeleteItem(), {
      wrapper: createWrapper(queryClient),
    })

    await act(async () => {
      await result.current.mutateAsync(specialItemId)
    })

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe(
      `${API_BASE}/api/items/${encodeURIComponent(specialItemId)}`
    )
    expect(jsonSpy).not.toHaveBeenCalled()
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: itemQueryKeys.lists(),
    })
    expect(removeSpy).toHaveBeenCalledWith({
      queryKey: itemQueryKeys.detail(specialItemId),
    })
    expect(
      queryClient.getQueryData(itemQueryKeys.detail(specialItemId))
    ).toBeUndefined()
  })
})
