import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import i18n from '@/i18n/config'
import type { SearchResultItem } from '@/services/search'
import { SearchResultCard } from './SearchResultCard'
import {
  createSearchSnippet,
  toRelevancePercent,
} from './search-result-card.utils'

const baseResult: SearchResultItem = {
  item_id: 'item-1',
  item_title: 'Graph Databases',
  content_type: 'webpage',
  chunk_id: 'chunk-1',
  chunk_content: 'Graph databases connect data as relationships.',
  score: 0.91,
  rank: 1,
}

describe('SearchResultCard', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders metadata, relevance, and typed detail navigation', async () => {
    render(<SearchResultCard result={baseResult} />, { initialPath: '/items' })

    await waitFor(() => {
      expect(screen.getByText('Graph Databases')).toBeInTheDocument()
    })

    expect(screen.getByText('Web Page')).toBeInTheDocument()
    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(screen.getByText('91%')).toBeInTheDocument()
    expect(screen.getByText('Relevance')).toBeInTheDocument()

    const detailLink = screen.getByRole('link', { name: /Graph Databases/i })
    expect(detailLink).toHaveAttribute('href', '/items/item-1')
  })

  it('truncates long snippets', async () => {
    const longResult: SearchResultItem = {
      ...baseResult,
      chunk_content: 'word '.repeat(60),
    }

    render(<SearchResultCard result={longResult} />, { initialPath: '/items' })

    await waitFor(() => {
      expect(
        screen.getByText(content => content.endsWith('…'))
      ).toBeInTheDocument()
    })
  })

  it('falls back to file metadata for unknown content types', async () => {
    const unknownContentTypeResult = {
      ...baseResult,
      content_type: 'custom-type',
      score: Number.NaN,
    } as unknown as SearchResultItem

    render(<SearchResultCard result={unknownContentTypeResult} />, {
      initialPath: '/items',
    })

    await waitFor(() => {
      expect(screen.getByText('File')).toBeInTheDocument()
    })
    expect(screen.getByText('0%')).toBeInTheDocument()
    expect(screen.getByLabelText('Relevance: 0%')).toBeInTheDocument()
  })

  it('clamps score display to 100 percent', async () => {
    const overflowScoreResult: SearchResultItem = {
      ...baseResult,
      score: 3,
    }

    render(<SearchResultCard result={overflowScoreResult} />, {
      initialPath: '/items',
    })

    await waitFor(() => {
      expect(screen.getByText('100%')).toBeInTheDocument()
    })
    expect(screen.getByLabelText('Relevance: 100%')).toBeInTheDocument()
  })
})

describe('SearchResultCard helpers', () => {
  it('normalizes and truncates snippets', () => {
    const snippet = createSearchSnippet('word '.repeat(60))

    expect(snippet.endsWith('…')).toBe(true)
    expect(snippet.length).toBeLessThanOrEqual(151)
  })

  it.each([
    { score: Number.NaN, expected: 0 },
    { score: -0.5, expected: 0 },
    { score: 0, expected: 0 },
    { score: 0.91, expected: 91 },
    { score: 3, expected: 100 },
  ])(
    'maps score=$score to relevance percent=$expected',
    ({ score, expected }) => {
      expect(toRelevancePercent(score)).toBe(expected)
    }
  )
})
