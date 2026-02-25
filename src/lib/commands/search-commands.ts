import { Search } from 'lucide-react'
import { useUIStore } from '@/store/ui-store'
import type { AppCommand } from './types'

export const searchCommands: AppCommand[] = [
  {
    id: 'focus-search',
    labelKey: 'commands.focusSearch.label',
    descriptionKey: 'commands.focusSearch.description',
    icon: Search,
    group: 'navigation',
    shortcut: '⌘+F',
    keywords: ['search', 'find', 'query'],

    execute: () => {
      const { setSearchFocused } = useUIStore.getState()
      setSearchFocused(true)
    },

    isAvailable: () => true,
  },
]
