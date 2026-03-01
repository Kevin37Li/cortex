import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ItemList } from '@/components/items'
import { SearchBar, SearchResults } from '@/components/search'

export const Route = createFileRoute('/items/')({
  component: ItemsIndexPage,
})

const SEARCH_DEBOUNCE_MS = 300

export function ItemsIndexPage() {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery)
    }, SEARCH_DEBOUNCE_MS)

    return () => clearTimeout(timer)
  }, [searchQuery])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b px-6 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold text-foreground">
            {t('nav.allItems')}
          </h1>
          <div className="w-full max-w-sm">
            <SearchBar value={searchQuery} onValueChange={setSearchQuery} />
          </div>
        </div>
      </div>
      {debouncedQuery.trim() ? (
        <SearchResults query={debouncedQuery} className="flex-1" />
      ) : (
        <ItemList className="flex-1" />
      )}
    </div>
  )
}
