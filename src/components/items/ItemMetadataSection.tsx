import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { Item } from '@/services/items'
import {
  getMetadataRecord,
  getMetadataString,
  getMetadataStringList,
} from './ItemMetadataSection.utils'

interface ItemMetadataSectionProps {
  metadata: Item['metadata']
  className?: string
}

export function ItemMetadataSection({
  metadata,
  className,
}: ItemMetadataSectionProps) {
  const { t } = useTranslation()
  const parsedMetadata = getMetadataRecord(metadata)
  if (!parsedMetadata) {
    return null
  }

  const summary = getMetadataString(parsedMetadata, 'summary')
  const concepts = getMetadataStringList(parsedMetadata, 'concepts')
  const entities = getMetadataStringList(parsedMetadata, 'entities')
  const hasContent =
    summary !== null || concepts.length > 0 || entities.length > 0

  if (!hasContent) {
    return null
  }

  return (
    <section
      className={cn('space-y-4', className)}
      aria-label={t('items.detail.metadata')}
    >
      <h2 className="text-lg font-semibold text-foreground">
        {t('items.detail.metadata')}
      </h2>

      {summary ? (
        <div className="space-y-1">
          <h3 className="text-sm font-medium text-foreground">
            {t('items.detail.summary')}
          </h3>
          <p className="text-sm whitespace-pre-wrap text-foreground/90">
            {summary}
          </p>
        </div>
      ) : null}

      {concepts.length > 0 ? (
        <div className="space-y-1">
          <h3 className="text-sm font-medium text-foreground">
            {t('items.detail.concepts')}
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {concepts.map((concept, index) => (
              <Badge key={`${concept}-${index}`} variant="outline">
                {concept}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      {entities.length > 0 ? (
        <div className="space-y-1">
          <h3 className="text-sm font-medium text-foreground">
            {t('items.detail.entities')}
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {entities.map((entity, index) => (
              <Badge key={`${entity}-${index}`} variant="outline">
                {entity}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}
