import { AlertCircle, Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { ItemGroup } from '@/components/ui/item'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useSearch, type SearchType } from '@/services/search'
import { SearchResultCard } from './SearchResultCard'

interface SearchResultsProps {
  query: string
  searchType?: SearchType
  limit?: number
  className?: string
}

export function SearchResults({
  query,
  searchType,
  limit,
  className,
}: SearchResultsProps) {
  const { t } = useTranslation()
  const normalizedQuery = query.trim()

  const searchParams = {
    query: normalizedQuery,
    ...(searchType ? { search_type: searchType } : {}),
    ...(limit !== undefined ? { limit } : {}),
  }

  const searchQuery = useSearch(searchParams)
  const results = searchQuery.data?.results ?? []
  const total = searchQuery.data?.total ?? 0

  if (!normalizedQuery) {
    return (
      <div className={cn('flex h-full min-h-0 flex-col p-3', className)}>
        <Empty className="flex-1">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Search />
            </EmptyMedia>
            <EmptyTitle>{t('search.prompt')}</EmptyTitle>
            <EmptyDescription>{t('search.promptDescription')}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      </div>
    )
  }

  if (searchQuery.isPending) {
    return (
      <div className={cn('flex h-full min-h-0 flex-col', className)}>
        <span className="sr-only" aria-live="polite">
          {t('search.loading')}
        </span>
        <ItemGroup className="p-3">
          {Array.from({ length: 6 }, (_, index) => (
            <div
              key={`search-skeleton-${index}`}
              className="rounded-lg border p-3"
            >
              <div className="flex items-center gap-3">
                <Skeleton className="size-4 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-3.5 w-2/3" />
                  <Skeleton className="h-3 w-full" />
                </div>
                <Skeleton className="h-8 w-12" />
              </div>
            </div>
          ))}
        </ItemGroup>
      </div>
    )
  }

  if (searchQuery.isError) {
    return (
      <div className={cn('flex h-full min-h-0 flex-col p-3', className)}>
        <Empty className="flex-1">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <AlertCircle />
            </EmptyMedia>
            <EmptyTitle>{t('search.error')}</EmptyTitle>
            <EmptyDescription>{t('search.errorDescription')}</EmptyDescription>
          </EmptyHeader>
          <Button
            type="button"
            variant="outline"
            onClick={() => void searchQuery.refetch()}
          >
            {t('search.retry')}
          </Button>
        </Empty>
      </div>
    )
  }

  if (results.length === 0) {
    return (
      <div className={cn('flex h-full min-h-0 flex-col p-3', className)}>
        <Empty className="flex-1">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Search />
            </EmptyMedia>
            <EmptyTitle>{t('search.noResults')}</EmptyTitle>
            <EmptyDescription>
              {t('search.noResultsDescription')}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      </div>
    )
  }

  return (
    <div className={cn('flex h-full min-h-0 flex-col', className)}>
      <div
        className="border-b px-3 py-2 text-xs text-muted-foreground"
        aria-live="polite"
      >
        {t('search.resultCount', { count: total })}
      </div>
      <ScrollArea className="flex-1">
        <ItemGroup className="p-3">
          {results.map(result => (
            <SearchResultCard
              key={`${result.item_id}-${result.chunk_id}`}
              result={result}
            />
          ))}
        </ItemGroup>
      </ScrollArea>
    </div>
  )
}
