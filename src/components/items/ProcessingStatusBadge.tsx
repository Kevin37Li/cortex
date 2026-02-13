import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'
import type { ProcessingStatus } from '@/services/items'

const statusLabelKeys: Record<ProcessingStatus, string> = {
  pending: 'items.status.pending',
  processing: 'items.status.processing',
  completed: 'items.status.completed',
  failed: 'items.status.failed',
}

const statusClasses: Record<ProcessingStatus, string> = {
  pending: 'border-transparent bg-muted text-muted-foreground',
  processing:
    'animate-pulse border-blue-400/40 bg-blue-500/10 text-blue-700 dark:text-blue-300',
  completed:
    'border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-300',
  failed: 'border-destructive/30 bg-destructive/10 text-destructive',
}

interface ProcessingStatusBadgeProps {
  status: ProcessingStatus
  stepLabel?: string
  onRetry?: () => void
  className?: string
}

export function ProcessingStatusBadge({
  status,
  stepLabel,
  onRetry,
  className,
}: ProcessingStatusBadgeProps) {
  const { t } = useTranslation()
  const showRetry = status === 'failed' && onRetry !== undefined

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Badge
        variant="outline"
        className={cn('h-6 gap-1.5 border px-2', statusClasses[status])}
      >
        {status === 'processing' ? <Spinner className="size-3" /> : null}
        <span>{t(statusLabelKeys[status])}</span>
        {stepLabel ? (
          <span className="text-[0.7rem] opacity-80">{stepLabel}</span>
        ) : null}
      </Badge>

      {showRetry ? (
        <Button type="button" variant="ghost" size="xs" onClick={onRetry}>
          {t('items.status.retry')}
        </Button>
      ) : null}
    </div>
  )
}
