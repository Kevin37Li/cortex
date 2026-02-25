import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { ItemList, ItemsSearchInput } from '@/components/items'

export const Route = createFileRoute('/items/')({
  component: ItemsIndexPage,
})

function ItemsIndexPage() {
  const { t } = useTranslation()

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b px-6 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold text-foreground">
            {t('nav.allItems')}
          </h1>
          <div className="w-full max-w-sm">
            <ItemsSearchInput />
          </div>
        </div>
      </div>
      <ItemList className="flex-1" />
    </div>
  )
}
