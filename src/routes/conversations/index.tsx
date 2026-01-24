import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { MessageSquare } from 'lucide-react'

export const Route = createFileRoute('/conversations/')({
  component: ConversationsIndexPage,
})

function ConversationsIndexPage() {
  const { t } = useTranslation()

  return (
    <div className="flex h-full flex-col items-center justify-center gap-4">
      <MessageSquare className="h-16 w-16 text-muted-foreground" />
      <h1 className="text-2xl font-semibold text-foreground">
        {t('nav.conversations')}
      </h1>
      <p className="text-muted-foreground">{t('conversations.emptyState')}</p>
    </div>
  )
}
