import type { FormEvent } from 'react'
import { useForm } from '@tanstack/react-form'
import { Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { notifications } from '@/lib/notifications'
import { useCreateItem } from '@/services/items'
import { useUIStore } from '@/store/ui-store'

interface QuickNoteFormValues {
  title: string
  content: string
}

const defaultValues: QuickNoteFormValues = {
  title: '',
  content: '',
}

function getFieldError(error: unknown): string | undefined {
  return typeof error === 'string' ? error : undefined
}

export function QuickNoteDialog() {
  const { t } = useTranslation()
  const quickNoteDialogOpen = useUIStore(state => state.quickNoteDialogOpen)
  const setQuickNoteDialogOpen = useUIStore(
    state => state.setQuickNoteDialogOpen
  )
  const createItemMutation = useCreateItem()

  const form = useForm({
    defaultValues,
    onSubmit: async ({ value }) => {
      try {
        await createItemMutation.mutateAsync({
          title: value.title.trim(),
          content: value.content.trim(),
          content_type: 'note',
        })

        setQuickNoteDialogOpen(false)
        form.reset()
        await notifications.success(t('notes.create.success'))
      } catch {
        await notifications.error(t('notes.create.error'))
      }
    },
  })

  const handleOpenChange = (open: boolean) => {
    setQuickNoteDialogOpen(open)
    if (!open) {
      form.reset()
    }
  }

  const handleCancel = () => {
    setQuickNoteDialogOpen(false)
    form.reset()
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    event.stopPropagation()
    void form.handleSubmit()
  }

  return (
    <Dialog open={quickNoteDialogOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{t('notes.create.title')}</DialogTitle>
          <DialogDescription>{t('notes.create.description')}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <form.Field
            name="title"
            validators={{
              onSubmit: ({ value }) =>
                !value.trim() ? t('notes.create.titleRequired') : undefined,
            }}
          >
            {field => {
              const error = getFieldError(field.state.meta.errors[0])
              const inputId = 'quick-note-title'

              return (
                <div className="space-y-2">
                  <Label htmlFor={inputId}>
                    {t('notes.create.titleLabel')}
                  </Label>
                  <Input
                    id={inputId}
                    autoFocus
                    value={field.state.value}
                    onChange={event => field.handleChange(event.target.value)}
                    onBlur={field.handleBlur}
                    placeholder={t('notes.create.titlePlaceholder')}
                    aria-invalid={Boolean(error)}
                  />
                  {error && <p className="text-sm text-destructive">{error}</p>}
                </div>
              )
            }}
          </form.Field>

          <form.Field
            name="content"
            validators={{
              onSubmit: ({ value }) =>
                !value.trim() ? t('notes.create.contentRequired') : undefined,
            }}
          >
            {field => {
              const error = getFieldError(field.state.meta.errors[0])
              const textareaId = 'quick-note-content'

              return (
                <div className="space-y-2">
                  <Label htmlFor={textareaId}>
                    {t('notes.create.contentLabel')}
                  </Label>
                  <Textarea
                    id={textareaId}
                    value={field.state.value}
                    onChange={event => field.handleChange(event.target.value)}
                    onBlur={field.handleBlur}
                    onKeyDown={event => {
                      if (
                        (event.metaKey || event.ctrlKey) &&
                        event.key === 'Enter'
                      ) {
                        event.preventDefault()
                        void form.handleSubmit()
                      }
                    }}
                    placeholder={t('notes.create.contentPlaceholder')}
                    className="min-h-40"
                    aria-invalid={Boolean(error)}
                  />
                  {error && <p className="text-sm text-destructive">{error}</p>}
                </div>
              )
            }}
          </form.Field>

          <form.Subscribe
            selector={state => [state.canSubmit, state.isSubmitting]}
          >
            {([canSubmit, isSubmitting]) => (
              <DialogFooter className="px-0 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCancel}
                  disabled={isSubmitting}
                >
                  {t('notes.create.cancel')}
                </Button>
                <Button type="submit" disabled={!canSubmit || isSubmitting}>
                  {isSubmitting && (
                    <Loader2
                      data-testid="quick-note-saving-spinner"
                      className="h-4 w-4 animate-spin"
                    />
                  )}
                  {isSubmitting
                    ? t('notes.create.saving')
                    : t('notes.create.submit')}
                </Button>
              </DialogFooter>
            )}
          </form.Subscribe>
        </form>
      </DialogContent>
    </Dialog>
  )
}
