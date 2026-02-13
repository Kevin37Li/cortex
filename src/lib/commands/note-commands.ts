import { NotebookPen } from 'lucide-react'
import { openQuickNoteDialog } from '@/lib/quick-note/open-quick-note'
import type { AppCommand } from './types'

export const noteCommands: AppCommand[] = [
  {
    id: 'create-note',
    labelKey: 'commands.createNote.label',
    descriptionKey: 'commands.createNote.description',
    icon: NotebookPen,
    group: 'notes',
    shortcut: '⌘+N',
    keywords: ['note', 'create', 'new', 'write'],

    execute: () => {
      openQuickNoteDialog()
    },
  },
]
