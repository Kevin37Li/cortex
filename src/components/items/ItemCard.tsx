import { Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import {
  Item as ListItem,
  ItemActions,
  ItemContent,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item'
import { Badge } from '@/components/ui/badge'
import { contentTypeConfig } from '@/lib/content-type'
import type { Item } from '@/services/items'
import { useProcessingStore } from '@/store/processing-store'
import { ProcessingStatusBadge } from './ProcessingStatusBadge'

const relativeTimeUnits: {
  unit: Intl.RelativeTimeFormatUnit
  ms: number
}[] = [
  { unit: 'year', ms: 1000 * 60 * 60 * 24 * 365 },
  { unit: 'month', ms: 1000 * 60 * 60 * 24 * 30 },
  { unit: 'week', ms: 1000 * 60 * 60 * 24 * 7 },
  { unit: 'day', ms: 1000 * 60 * 60 * 24 },
  { unit: 'hour', ms: 1000 * 60 * 60 },
  { unit: 'minute', ms: 1000 * 60 },
  { unit: 'second', ms: 1000 },
]

const relativeFormatterCache = new Map<string, Intl.RelativeTimeFormat>()

function getRelativeFormatter(locale: string): Intl.RelativeTimeFormat {
  let fmt = relativeFormatterCache.get(locale)
  if (!fmt) {
    fmt = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
    relativeFormatterCache.set(locale, fmt)
  }
  return fmt
}

function formatRelativeCreatedAt(timestamp: string, locale: string) {
  const createdAt = new Date(timestamp)
  if (Number.isNaN(createdAt.getTime())) {
    return timestamp
  }

  const deltaMs = createdAt.getTime() - Date.now()
  const formatter = getRelativeFormatter(locale)

  for (const timeUnit of relativeTimeUnits) {
    if (Math.abs(deltaMs) >= timeUnit.ms || timeUnit.unit === 'second') {
      const value = Math.round(deltaMs / timeUnit.ms)
      return formatter.format(value, timeUnit.unit)
    }
  }

  return timestamp
}

interface ItemCardProps {
  item: Item
  onRetryProcessing?: (item: Item) => void
}

export function ItemCard({ item, onRetryProcessing }: ItemCardProps) {
  const { t, i18n } = useTranslation()
  const processingUpdate = useProcessingStore(
    state => state.processingByItemId[item.id]
  )
  const { icon: ContentTypeIcon, labelKey } =
    contentTypeConfig[item.content_type] ?? contentTypeConfig.file
  const relativeCreatedAt = formatRelativeCreatedAt(
    item.created_at,
    i18n.language
  )
  const liveStatus = processingUpdate?.status ?? item.processing_status
  const stepLabel = processingUpdate
    ? t(`items.processing.step.${processingUpdate.step}`)
    : undefined
  const retryHandler = onRetryProcessing
    ? () => onRetryProcessing(item)
    : undefined

  return (
    <ListItem variant="outline" size="sm" className="gap-0 p-0">
      <Link
        to="/items/$id"
        params={{ id: item.id }}
        className="flex min-w-0 flex-1 items-center gap-3 rounded-lg px-3 py-2.5 text-start"
      >
        <ItemMedia variant="icon" className="text-muted-foreground">
          <ContentTypeIcon />
        </ItemMedia>

        <ItemContent className="min-w-0">
          <ItemTitle className="max-w-full">{item.title}</ItemTitle>
          <div className="text-muted-foreground mt-1 flex items-center gap-2 text-xs">
            <Badge variant="outline" data-icon="inline-start">
              <ContentTypeIcon />
              <span>{t(labelKey)}</span>
            </Badge>
            <span>{relativeCreatedAt}</span>
          </div>
        </ItemContent>
      </Link>

      <ItemActions className="pe-3">
        <ProcessingStatusBadge
          status={liveStatus}
          stepLabel={stepLabel}
          onRetry={retryHandler}
        />
      </ItemActions>
    </ListItem>
  )
}
