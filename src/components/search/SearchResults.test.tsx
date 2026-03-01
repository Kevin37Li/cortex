import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@/test/test-utils'
import i18n from '@/i18n/config'
import type { SearchResponse } from '@/services/search'
import { SearchResults } from './SearchResults'

vi.mock('@/services/search', async () => {
  const actual = await vi.importActual('@/services/search')

  return {
    ...actual,
    useSearch: vi.fn(),
  }
})

const { useSearch } = await import('@/services/search')

type UseSearchResult = ReturnType<typeof useSearch>

const useSearchMock = vi.mocked(useSearch)

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

function createQueryResult(
  overrides: Partial<UseSearchResult>
): UseSearchResult {
  return {
    data: undefined,
    error: null,
    isError: false,
    isPending: false,
    isFetching: false,
    refetch: vi.fn(),
    ...overrides,
  } as UseSearchResult
}

describe('SearchResults', () => {
  beforeEach(async () => {
    useSearchMock.mockReset()
    await i18n.changeLanguage('en')
  })

  it('normalizes query props and renders prompt state when query is empty', async () => {
    useSearchMock.mockReturnValue(createQueryResult({}))

    render(<SearchResults query="   " />)

    await waitFor(() => {
      expect(useSearchMock).toHaveBeenCalledWith({ query: '' })
    })

    expect(
      await screen.findByText('Search your knowledge base')
    ).toBeInTheDocument()
    expect(
      screen.getByText('Find items using natural language or keywords')
    ).toBeInTheDocument()
  })

  it('renders loading state while search is pending', async () => {
    useSearchMock.mockReturnValue(createQueryResult({ isPending: true }))

    render(<SearchResults query="graph" />)

    expect(await screen.findByText('Searching...')).toBeInTheDocument()
  })

  it('renders error state and retries on action', async () => {
    const refetch = vi.fn()
    useSearchMock.mockReturnValue(
      createQueryResult({
        isError: true,
        error: new Error('Search failed'),
        refetch,
      })
    )

    render(<SearchResults query="graph" />)

    fireEvent.click(await screen.findByRole('button', { name: 'Retry' }))

    await waitFor(() => {
      expect(refetch).toHaveBeenCalledTimes(1)
    })
  })

  it('renders no-results state', async () => {
    useSearchMock.mockReturnValue(
      createQueryResult({
        data: {
          ...sampleResponse,
          total: 0,
          results: [],
        },
      })
    )

    render(<SearchResults query="graph" />)

    expect(await screen.findByText('No results found')).toBeInTheDocument()
    expect(
      screen.getByText('Try different keywords or check your spelling')
    ).toBeInTheDocument()
  })

  it('renders result cards and count from useSearch', async () => {
    useSearchMock.mockReturnValue(
      createQueryResult({
        data: sampleResponse,
      })
    )

    render(<SearchResults query="  graph  " />, { initialPath: '/items' })

    await waitFor(() => {
      expect(useSearchMock).toHaveBeenCalledWith({ query: 'graph' })
    })

    await waitFor(() => {
      expect(screen.getByText('1 result')).toBeInTheDocument()
    })

    expect(screen.getByRole('list')).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(1)
    expect(screen.getByText('Graph Databases')).toBeInTheDocument()
  })
})
