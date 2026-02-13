import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { ItemList } from '@/components/items'

export const Route = createFileRoute('/items/')({
  component: ItemsIndexPage,
})

function ItemsIndexPage() {
  const { t } = useTranslation()

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b px-6 py-3">
        <h1 className="text-xl font-semibold text-foreground">
          {t('nav.allItems')}
        </h1>
      </div>
      <ItemList className="flex-1" />
    </div>
  )
}
