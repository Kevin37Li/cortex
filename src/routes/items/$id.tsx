import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

export const Route = createFileRoute('/items/$id')({
  component: ItemDetailPage,
})

function ItemDetailPage() {
  const { id } = Route.useParams()
  const { t } = useTranslation()

  return (
    <div className="flex h-full flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-semibold text-foreground">
        {t('items.detail.title')}
      </h1>
      <p className="text-muted-foreground">
        {t('items.detail.viewing', { id })}
      </p>
    </div>
  )
}
