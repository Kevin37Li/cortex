import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

export const Route = createFileRoute('/conversations/$id')({
  component: ConversationDetailPage,
})

function ConversationDetailPage() {
  const { id } = Route.useParams()
  const { t } = useTranslation()

  return (
    <div className="flex h-full flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-semibold text-foreground">
        {t('conversations.detail.title')}
      </h1>
      <p className="text-muted-foreground">
        {t('conversations.detail.viewing', { id })}
      </p>
    </div>
  )
}
