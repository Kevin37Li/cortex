import { Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import {
  Item,
  ItemContent,
  ItemMedia,
  ItemTitle,
  ItemActions,
} from '@/components/ui/item'
import { Badge } from '@/components/ui/badge'
import { contentTypeConfig } from '@/lib/content-type'
import { cn } from '@/lib/utils'
import type { SearchResultItem } from '@/services/search'
import {
  createSearchSnippet,
  toRelevancePercent,
} from './search-result-card.utils'

interface SearchResultCardProps {
  result: SearchResultItem
  className?: string
}

export function SearchResultCard({ result, className }: SearchResultCardProps) {
  const { t } = useTranslation()
  const { icon: ContentTypeIcon, labelKey } =
    contentTypeConfig[result.content_type] ?? contentTypeConfig.file
  const relevancePercent = toRelevancePercent(result.score)
  const snippet = createSearchSnippet(result.chunk_content)

  return (
    <Item
      variant="outline"
      size="sm"
      className={cn('gap-0 p-0', className)}
      role="listitem"
    >
      <Link
        to="/items/$id"
        params={{ id: result.item_id }}
        className="flex min-w-0 flex-1 items-center gap-3 rounded-lg px-3 py-2.5 text-start"
      >
        <ItemMedia variant="icon" className="text-muted-foreground">
          <ContentTypeIcon />
        </ItemMedia>

        <ItemContent className="min-w-0">
          <ItemTitle className="max-w-full">{result.item_title}</ItemTitle>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" data-icon="inline-start">
              <ContentTypeIcon />
              <span>{t(labelKey)}</span>
            </Badge>
            <span className="truncate text-start">{snippet}</span>
          </div>
        </ItemContent>

        {/* Score display intentionally inside Link — no interactive actions here */}
        <ItemActions className="shrink-0 flex-col items-end gap-1 text-xs text-muted-foreground">
          <span>{`#${result.rank}`}</span>
          <div
            aria-label={`${t('search.relevance')}: ${relevancePercent}%`}
            className="flex flex-col items-end gap-1"
          >
            <span aria-hidden="true">{`${relevancePercent}%`}</span>
            <div
              className="bg-muted h-1.5 w-14 overflow-hidden rounded-full"
              aria-hidden="true"
            >
              <div
                className="bg-primary h-full rounded-full"
                style={{ width: `${relevancePercent}%` }}
              />
            </div>
            <span aria-hidden="true">{t('search.relevance')}</span>
          </div>
        </ItemActions>
      </Link>
    </Item>
  )
}
