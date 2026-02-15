import { AlertCircle, ArrowLeft, ExternalLink } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from '@tanstack/react-router'
import { openUrl } from '@tauri-apps/plugin-opener'
import { toast } from 'sonner'
import { Button, buttonVariants } from '@/components/ui/button'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiRequestError } from '@/lib/api-config'
import { logger } from '@/lib/logger'
import { cn } from '@/lib/utils'
import { useItem, useRetryProcessing, type ContentType } from '@/services/items'
import { parseItemMetadata } from './ItemMetadataSection.utils'
import { ItemMetadataSection } from './ItemMetadataSection'
import { ProcessingStatusBadge } from './ProcessingStatusBadge'

const contentTypeLabelKeys: Record<ContentType, string> = {
  webpage: 'items.contentType.webpage',
  note: 'items.contentType.note',
  file: 'items.contentType.file',
}

const absoluteFormatterCache = new Map<string, Intl.DateTimeFormat>()

function formatAbsoluteCreatedAt(timestamp: string, locale: string): string {
  const createdAt = new Date(timestamp)
  if (Number.isNaN(createdAt.getTime())) {
    return timestamp
  }

  let formatter = absoluteFormatterCache.get(locale)
  if (!formatter) {
    formatter = new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
    absoluteFormatterCache.set(locale, formatter)
  }

  return formatter.format(createdAt)
}

interface ItemDetailProps {
  itemId: string
  className?: string
}

export function ItemDetail({ itemId, className }: ItemDetailProps) {
  const { t, i18n } = useTranslation()
  const itemQuery = useItem(itemId)
  const retryProcessingMutation = useRetryProcessing()

  const backButton = (
    <Link
      to="/items"
      className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }))}
    >
      <ArrowLeft />
      <span>{t('items.detail.back')}</span>
    </Link>
  )

  if (itemQuery.isPending) {
    return (
      <div className={cn('flex h-full min-h-0 flex-col', className)}>
        <div className="border-b px-6 py-3">{backButton}</div>
        <div className="flex-1 space-y-6 p-6">
          <span className="sr-only">{t('items.detail.loading')}</span>
          <div className="space-y-3">
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-5 w-1/3" />
          </div>
          <Skeleton className="h-36 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>
    )
  }

  if (itemQuery.isError) {
    const isNotFound =
      (itemQuery.error instanceof ApiRequestError &&
        itemQuery.error.status === 404 &&
        (itemQuery.error.code === 'item_not_found' ||
          itemQuery.error.message.includes('Item not found:'))) ||
      (itemQuery.error instanceof Error &&
        itemQuery.error.message.includes('Item not found:'))

    return (
      <div className={cn('flex h-full min-h-0 flex-col', className)}>
        <div className="border-b px-6 py-3">{backButton}</div>
        <div className="flex min-h-0 flex-1 p-6">
          <Empty className="border">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <AlertCircle />
              </EmptyMedia>
              <EmptyTitle>
                {isNotFound
                  ? t('items.detail.notFound')
                  : t('items.detail.error')}
              </EmptyTitle>
              <EmptyDescription>
                {isNotFound
                  ? t('items.detail.notFoundDescription')
                  : t('items.detail.errorDescription')}
              </EmptyDescription>
            </EmptyHeader>
            {!isNotFound ? (
              <EmptyContent>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void itemQuery.refetch()}
                >
                  {t('items.list.retry')}
                </Button>
              </EmptyContent>
            ) : null}
          </Empty>
        </div>
      </div>
    )
  }

  const item = itemQuery.data
  const contentTypeLabelKey =
    contentTypeLabelKeys[item.content_type] ?? contentTypeLabelKeys.file
  const createdAt = formatAbsoluteCreatedAt(item.created_at, i18n.language)
  const metadata = parseItemMetadata(item.metadata)
  const processingError = metadata?.processingError ?? null
  const errorStep = metadata?.errorStep ?? null

  const handleRetryProcessing = async () => {
    try {
      const response = await retryProcessingMutation.mutateAsync(item.id)
      if (response.outcome === 'retried') {
        toast.success(t('items.detail.retrySucceeded'))
      } else if (response.outcome === 'already_queued') {
        toast.info(t('items.detail.retryQueued'))
      } else {
        toast.warning(t('items.detail.retryNotInQueue'))
      }
    } catch {
      toast.error(t('toast.error.generic'))
    }
  }

  const handleOpenSource = async () => {
    if (!item.source_url) {
      return
    }

    try {
      await openUrl(item.source_url)
    } catch (error) {
      logger.error('Failed to open item source URL', {
        itemId: item.id,
        sourceUrl: item.source_url,
        error,
      })
      toast.error(t('items.detail.openSourceFailed'))
    }
  }

  return (
    <div className={cn('flex h-full min-h-0 flex-col', className)}>
      <div className="border-b px-6 py-3">{backButton}</div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <article className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
          <header className="space-y-3">
            <h1 className="text-2xl font-semibold text-foreground">
              {item.title}
            </h1>
            <div className="text-muted-foreground flex flex-wrap items-center gap-2 text-sm">
              <Badge variant="outline">{t(contentTypeLabelKey)}</Badge>
              <span>•</span>
              <span>
                {t('items.detail.created')}: {createdAt}
              </span>
            </div>
          </header>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold text-foreground">
              {t('items.detail.content')}
            </h2>
            <div className="whitespace-pre-wrap rounded-lg border p-4 text-sm leading-6 text-foreground">
              {item.content}
            </div>
          </section>

          {item.source_url ? (
            <section className="space-y-2">
              <h2 className="text-lg font-semibold text-foreground">
                {t('items.detail.source')}
              </h2>
              <Button
                type="button"
                variant="outline"
                onClick={() => void handleOpenSource()}
                className="max-w-full justify-start"
              >
                <ExternalLink />
                <span className="truncate">{item.source_url}</span>
              </Button>
            </section>
          ) : null}

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-foreground">
              {t('items.detail.processing')}
            </h2>
            <div className="flex flex-wrap items-center gap-3">
              <ProcessingStatusBadge status={item.processing_status} />
              {item.processing_status === 'failed' ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void handleRetryProcessing()}
                  disabled={retryProcessingMutation.isPending}
                >
                  {retryProcessingMutation.isPending
                    ? t('items.detail.retrying')
                    : t('items.detail.retryProcessing')}
                </Button>
              ) : null}
            </div>

            {item.processing_status === 'failed' &&
            (processingError || errorStep) ? (
              <div className="space-y-1 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm">
                <p className="font-medium text-destructive">
                  {t('items.detail.processingFailed')}
                </p>
                {errorStep ? (
                  <p className="text-foreground">
                    {t('items.detail.errorStep')}: {errorStep}
                  </p>
                ) : null}
                {processingError ? (
                  <p className="text-destructive">{processingError}</p>
                ) : null}
              </div>
            ) : null}
          </section>

          {item.processing_status === 'completed' ? (
            <ItemMetadataSection metadata={metadata} />
          ) : null}
        </article>
      </div>
    </div>
  )
}
