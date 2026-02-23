import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createMockResponse,
  createTestQueryClient,
  createWrapper,
} from '@/test-utils/query-test-helpers'
import type { SearchResponse } from './search'

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
const { searchQueryKeys, useSearch } = await import('./search')

const fetchMock = vi.fn()

const sampleResponse: SearchResponse = {
  results: [
    {
      item_id: 'item-1',
      item_title: 'Graph Databases',
      content_type: 'webpage',
      chunk_id: 'chunk-1',
      chunk_content: 'Graph databases connect data as relationships.',
      score: 0.91,
      rank: 1,
    },
  ],
  total: 1,
  query: 'graph',
  search_type: 'hybrid',
}

describe('searchQueryKeys', () => {
  it('creates expected base query keys', () => {
    expect(searchQueryKeys.all).toEqual(['search'])
    expect(searchQueryKeys.searches()).toEqual(['search', 'searches'])
  })

  it('creates unique keys for query/search_type/limit changes', () => {
    const baseline = searchQueryKeys.search({ query: 'graph' })
    const differentQuery = searchQueryKeys.search({ query: 'vector' })
    const differentType = searchQueryKeys.search({
      query: 'graph',
      search_type: 'fts',
    })
    const differentLimit = searchQueryKeys.search({ query: 'graph', limit: 10 })

    expect(baseline).not.toEqual(differentQuery)
    expect(baseline).not.toEqual(differentType)
    expect(baseline).not.toEqual(differentLimit)
  })

  it('creates equal keys for equivalent params and whitespace variants', () => {
    expect(searchQueryKeys.search({ query: 'graph' })).toEqual(
      searchQueryKeys.search({
        query: 'graph',
        search_type: 'hybrid',
        limit: 20,
      })
    )
    expect(searchQueryKeys.search({ query: '  graph  ' })).toEqual(
      searchQueryKeys.search({ query: 'graph' })
    )
  })

  it('preserves interior whitespace in query', () => {
    const key = searchQueryKeys.search({ query: 'graph  database' })
    const normalized = key[2]
    expect(normalized.query).toBe('graph  database')
  })
})

describe('search services', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  it('builds POST request with normalized JSON body', async () => {
    fetchMock.mockResolvedValue(createMockResponse({ body: sampleResponse }))

    const queryClient = createTestQueryClient()
    const { result } = renderHook(
      () =>
        useSearch({
          query: '  graph  ',
          search_type: 'vector',
          limit: 5,
        }),
      {
        wrapper: createWrapper(queryClient),
      }
    )

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual(sampleResponse)

    const [url, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${API_BASE}/api/search/`)
    expect(requestInit.method).toBe('POST')
    expect(requestInit.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(requestInit.body).toBe(
      JSON.stringify({
        query: 'graph',
        search_type: 'vector',
        limit: 5,
      })
    )
  })

  it('uses default search_type and limit when omitted', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({
        body: { ...sampleResponse, search_type: 'hybrid', query: 'graph' },
      })
    )

    const queryClient = createTestQueryClient()
    const { result } = renderHook(() => useSearch({ query: 'graph' }), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    const [, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(requestInit.body).toBe(
      JSON.stringify({
        query: 'graph',
        search_type: 'hybrid',
        limit: 20,
      })
    )
  })

  it.each(['', '   '])(
    'disables query when query is empty/whitespace-only: "%s"',
    async query => {
      const queryClient = createTestQueryClient()
      const { result } = renderHook(() => useSearch({ query }), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => {
        expect(result.current.fetchStatus).toBe('idle')
      })

      expect(result.current.status).toBe('pending')
      expect(fetchMock).not.toHaveBeenCalled()
    }
  )

  it('propagates backend errors from apiFetch', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({
        status: 500,
        body: {
          error: 'search_failed',
          message: 'Search failed for query: graph',
        },
      })
    )

    const queryClient = createTestQueryClient()
    const { result } = renderHook(() => useSearch({ query: 'graph' }), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    expect((result.current.error as Error).message).toBe(
      'Search failed for query: graph'
    )
    expect(logger.error).toHaveBeenCalledTimes(1)
    expect(logger.error).toHaveBeenCalledWith(
      'API request failed',
      expect.objectContaining({
        path: '/api/search/',
        status: 500,
        error: 'search_failed',
        message: 'Search failed for query: graph',
      })
    )
  })

  it('propagates network request failures from apiFetch', async () => {
    fetchMock.mockRejectedValue(new Error('connection refused'))

    const queryClient = createTestQueryClient()
    const { result } = renderHook(() => useSearch({ query: 'graph' }), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    expect((result.current.error as Error).message).toBe(
      'Network request failed'
    )
    expect(logger.error).toHaveBeenCalledTimes(1)
    expect(logger.error).toHaveBeenCalledWith(
      'Network request failed',
      expect.objectContaining({
        path: '/api/search/',
      })
    )
  })
})
