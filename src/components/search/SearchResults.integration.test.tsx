import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import i18n from '@/i18n/config'
import { API_BASE } from '@/lib/api-config'
import type { SearchResponse } from '@/services/search'
import { createMockResponse } from '@/test-utils/query-test-helpers'
import { SearchResults } from './SearchResults'

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

describe('SearchResults integration', () => {
  beforeEach(async () => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
    await i18n.changeLanguage('en')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uses the real useSearch hook to request and render results', async () => {
    fetchMock.mockResolvedValue(createMockResponse({ body: sampleResponse }))

    render(<SearchResults query="  graph  " />, { initialPath: '/items' })

    await waitFor(() => {
      expect(screen.getByText('1 result')).toBeInTheDocument()
    })

    expect(screen.getByText('Graph Databases')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /Graph Databases/i })
    ).toHaveAttribute('href', '/items/item-1')

    const [url, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${API_BASE}/api/search/`)
    expect(requestInit.method).toBe('POST')
    expect(requestInit.body).toBe(
      JSON.stringify({
        query: 'graph',
        search_type: 'hybrid',
        limit: 20,
      })
    )
  })
})
