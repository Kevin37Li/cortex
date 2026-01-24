import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { FileText } from 'lucide-react'

export const Route = createFileRoute('/items/')({
  component: ItemsIndexPage,
})

function ItemsIndexPage() {
  const { t } = useTranslation()

  return (
    <div className="flex h-full flex-col items-center justify-center gap-4">
      <FileText className="h-16 w-16 text-muted-foreground" />
      <h1 className="text-2xl font-semibold text-foreground">
        {t('nav.allItems')}
      </h1>
      <p className="text-muted-foreground">{t('items.emptyState')}</p>
    </div>
  )
}
