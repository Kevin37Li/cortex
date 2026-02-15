import { useRef, useState } from 'react'
import { AlertCircle, FileText } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { keepPreviousData } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { ItemGroup } from '@/components/ui/item'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useItems, useRetryProcessing, type Item } from '@/services/items'
import { ItemCard } from './ItemCard'

const DEFAULT_PAGE_SIZE = 20

function normalizePageSize(pageSize: number): number {
  if (!Number.isFinite(pageSize) || pageSize < 1) {
    return DEFAULT_PAGE_SIZE
  }

  return Math.floor(pageSize)
}

/**
 * Build an array of page numbers to display in the pagination bar.
 * Always shows first, last, current, and one neighbor on each side.
 * Gaps are represented by `null` (rendered as ellipsis).
 */
function getPageNumbers(
  currentPage: number,
  totalPages: number
): (number | null)[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }

  const pages: (number | null)[] = [1]
  const rangeStart = Math.max(2, currentPage - 1)
  const rangeEnd = Math.min(totalPages - 1, currentPage + 1)

  if (rangeStart > 2) pages.push(null)
  for (let i = rangeStart; i <= rangeEnd; i++) pages.push(i)
  if (rangeEnd < totalPages - 1) pages.push(null)

  pages.push(totalPages)
  return pages
}

interface ItemListProps {
  className?: string
  pageSize?: number
}

export function ItemList({
  className,
  pageSize = DEFAULT_PAGE_SIZE,
}: ItemListProps) {
  const { t } = useTranslation()
  const retryProcessingMutation = useRetryProcessing()
  const retryingItemIdsRef = useRef(new Set<string>())
  const resolvedPageSize = normalizePageSize(pageSize)
  const [currentPage, setCurrentPage] = useState(1)

  const offset = (currentPage - 1) * resolvedPageSize

  const itemsQuery = useItems(
    { offset, limit: resolvedPageSize },
    { placeholderData: keepPreviousData }
  )
  const items = itemsQuery.data?.items ?? []
  const total = itemsQuery.data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / resolvedPageSize))
  const isPageTransition = itemsQuery.isFetching && itemsQuery.isPlaceholderData

  // Adjust state during render when page exceeds total (e.g. after deletion).
  // This is the React-recommended pattern for derived state adjustment.
  // The `total > 0` guard is essential — without it, when data is undefined
  // (total falls back to 0), totalPages becomes 1, causing an infinite
  // re-render loop as currentPage is set to 1 repeatedly.
  if (total > 0 && currentPage > totalPages) {
    setCurrentPage(totalPages)
  }

  if (itemsQuery.isPending) {
    return (
      <div className={cn('flex h-full min-h-0 flex-col', className)}>
        <span className="sr-only">{t('items.list.loading')}</span>
        <ItemGroup className="p-3">
          {Array.from({ length: resolvedPageSize }, (_, index) => (
            <div
              key={`item-skeleton-${index}`}
              className="rounded-lg border p-3"
            >
              <div className="flex items-center gap-3">
                <Skeleton className="size-4 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-3.5 w-2/3" />
                  <Skeleton className="h-3 w-1/3" />
                </div>
                <Skeleton className="h-5 w-24 rounded-full" />
              </div>
            </div>
          ))}
        </ItemGroup>
      </div>
    )
  }

  if (itemsQuery.isError) {
    return (
      <div className={cn('flex h-full min-h-0 flex-col p-3', className)}>
        <Empty className="flex-1">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <AlertCircle />
            </EmptyMedia>
            <EmptyTitle>{t('items.list.error')}</EmptyTitle>
          </EmptyHeader>
          <EmptyContent>
            <Button
              type="button"
              variant="outline"
              onClick={() => void itemsQuery.refetch()}
            >
              {t('items.list.retry')}
            </Button>
          </EmptyContent>
        </Empty>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className={cn('flex h-full min-h-0 flex-col p-3', className)}>
        <Empty className="flex-1">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FileText />
            </EmptyMedia>
            <EmptyTitle>{t('items.list.empty')}</EmptyTitle>
            <EmptyDescription>
              {t('items.list.emptyDescription')}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      </div>
    )
  }

  const pageNumbers = getPageNumbers(currentPage, totalPages)

  const handleRetryProcessing = (item: Item) => {
    if (retryingItemIdsRef.current.has(item.id)) {
      return
    }

    retryingItemIdsRef.current.add(item.id)

    void retryProcessingMutation
      .mutateAsync(item.id)
      .then(response => {
        if (response.outcome === 'retried') {
          toast.success(t('items.detail.retrySucceeded'))
        } else if (response.outcome === 'already_queued') {
          toast.info(t('items.detail.retryQueued'))
        } else {
          toast.warning(t('items.detail.retryNotInQueue'))
        }
      })
      .catch(() => {
        toast.error(t('toast.error.generic'))
      })
      .finally(() => {
        retryingItemIdsRef.current.delete(item.id)
      })
  }

  return (
    <div className={cn('flex h-full min-h-0 flex-col', className)}>
      <ScrollArea className="flex-1">
        <ItemGroup className={cn('p-3', isPageTransition && 'opacity-60')}>
          {items.map(item => (
            <ItemCard
              key={item.id}
              item={item}
              onRetryProcessing={handleRetryProcessing}
            />
          ))}
        </ItemGroup>
      </ScrollArea>

      {totalPages > 1 ? (
        <div className="border-t px-3 py-3">
          <Pagination ariaLabel={t('items.list.pagination')}>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  text={t('items.list.previousPage')}
                  ariaLabel={t('items.list.goToPreviousPage')}
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                />
              </PaginationItem>

              {pageNumbers.map((page, index) =>
                page === null ? (
                  <PaginationItem key={`ellipsis-${index}`}>
                    <PaginationEllipsis moreLabel={t('items.list.morePages')} />
                  </PaginationItem>
                ) : (
                  <PaginationItem key={page}>
                    <PaginationLink
                      isActive={page === currentPage}
                      onClick={() => setCurrentPage(page)}
                    >
                      {page}
                    </PaginationLink>
                  </PaginationItem>
                )
              )}

              <PaginationItem>
                <PaginationNext
                  text={t('items.list.nextPage')}
                  ariaLabel={t('items.list.goToNextPage')}
                  onClick={() =>
                    setCurrentPage(p => Math.min(totalPages, p + 1))
                  }
                  disabled={currentPage === totalPages}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>

          <p className="text-muted-foreground mt-2 text-center text-xs">
            {t('items.list.pageIndicator', {
              current: currentPage,
              total: totalPages,
            })}
          </p>
        </div>
      ) : null}
    </div>
  )
}
