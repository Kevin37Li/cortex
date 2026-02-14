import { useState } from 'react'
import { FileUp, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { importFile } from '@/lib/file-import'
import { useCreateItem } from '@/services/items'

export function FileImportButton() {
  const { t } = useTranslation()
  const createItemMutation = useCreateItem()
  const [readingFile, setReadingFile] = useState(false)

  const isImporting = readingFile || createItemMutation.isPending

  const handleImportClick = async () => {
    if (isImporting) {
      return
    }

    setReadingFile(true)

    try {
      await importFile({
        createItem: async data => {
          // Clear readingFile before mutateAsync so isPending takes over seamlessly
          setReadingFile(false)
          return createItemMutation.mutateAsync(data)
        },
        t,
      })
    } finally {
      setReadingFile(false)
    }
  }

  return (
    <Button
      variant="outline"
      className="w-full justify-start gap-2"
      onClick={() => {
        void handleImportClick()
      }}
      disabled={isImporting}
    >
      {isImporting ? (
        <Loader2
          data-testid="file-import-loading-spinner"
          className="h-4 w-4 shrink-0 animate-spin"
        />
      ) : (
        <FileUp className="h-4 w-4 shrink-0" />
      )}
      <span>
        {isImporting ? t('items.import.importing') : t('items.import.button')}
      </span>
    </Button>
  )
}
