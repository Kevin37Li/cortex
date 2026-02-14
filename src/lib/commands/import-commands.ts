import { FileUp } from 'lucide-react'
import { importFile } from '@/lib/file-import'
import { queryClient } from '@/lib/query-client'
import { createItem, itemQueryKeys } from '@/services/items'
import type { AppCommand } from './types'

export const importCommands: AppCommand[] = [
  {
    id: 'import-file',
    labelKey: 'commands.importFile.label',
    descriptionKey: 'commands.importFile.description',
    icon: FileUp,
    group: 'notes',
    keywords: ['import', 'file', 'markdown', 'text', 'upload'],

    execute: async () => {
      await importFile({
        createItem: async data => {
          const createdItem = await createItem(data)
          await queryClient.invalidateQueries({
            queryKey: itemQueryKeys.lists(),
          })
          return createdItem
        },
      })
    },
  },
]
