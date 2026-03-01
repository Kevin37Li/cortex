import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@/test/test-utils'
import i18n from '@/i18n/config'

vi.mock('@/components/items', () => ({
  ItemList: ({ className }: { className?: string }) => (
    <div className={className} data-testid="item-list">
      item-list
    </div>
  ),
}))

vi.mock('@/components/search', () => ({
  SearchBar: ({
    value,
    onValueChange,
    className,
  }: {
    value: string
    onValueChange: (value: string) => void
    className?: string
  }) => (
    <input
      type="search"
      aria-label="Search your knowledge base"
      className={className}
      value={value}
      onChange={event => onValueChange(event.target.value)}
    />
  ),
  SearchResults: ({
    query,
    className,
  }: {
    query: string
    className?: string
  }) => (
    <div className={className} data-testid="search-results">
      {query}
    </div>
  ),
}))

const { ItemsIndexPage } = await import('./index')

describe('ItemsIndexPage', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('debounces query updates and toggles between list and search results', async () => {
    render(<ItemsIndexPage />, { initialPath: '/items' })

    const searchInput = await screen.findByRole('searchbox', {
      name: 'Search your knowledge base',
    })
    await screen.findByTestId('item-list')

    vi.useFakeTimers()

    expect(screen.getByTestId('item-list')).toBeInTheDocument()
    expect(screen.queryByTestId('search-results')).not.toBeInTheDocument()

    fireEvent.change(searchInput, { target: { value: 'graph' } })

    act(() => {
      vi.advanceTimersByTime(299)
    })

    expect(screen.getByTestId('item-list')).toBeInTheDocument()
    expect(screen.queryByTestId('search-results')).not.toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(1)
    })

    expect(screen.getByTestId('search-results')).toHaveTextContent('graph')

    fireEvent.change(searchInput, { target: { value: '' } })

    act(() => {
      vi.advanceTimersByTime(300)
    })

    expect(screen.getByTestId('item-list')).toBeInTheDocument()
    expect(screen.queryByTestId('search-results')).not.toBeInTheDocument()
  })
})
