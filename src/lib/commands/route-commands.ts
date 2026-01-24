import { FileText, MessageSquare, Settings } from 'lucide-react'
import { router } from '@/lib/router'
import type { AppCommand } from './types'

export const routeCommands: AppCommand[] = [
  {
    id: 'go-to-items',
    labelKey: 'commands.goToItems.label',
    descriptionKey: 'commands.goToItems.description',
    icon: FileText,
    group: 'navigation',
    keywords: ['items', 'all', 'list', 'navigate', 'go'],

    execute: () => {
      router.navigate({ to: '/items' })
    },
  },

  {
    id: 'go-to-conversations',
    labelKey: 'commands.goToConversations.label',
    descriptionKey: 'commands.goToConversations.description',
    icon: MessageSquare,
    group: 'navigation',
    keywords: ['conversations', 'chat', 'messages', 'navigate', 'go'],

    execute: () => {
      router.navigate({ to: '/conversations' })
    },
  },

  {
    id: 'go-to-settings',
    labelKey: 'commands.goToSettings.label',
    descriptionKey: 'commands.goToSettings.description',
    icon: Settings,
    group: 'navigation',
    keywords: ['settings', 'preferences', 'config', 'navigate', 'go'],

    execute: () => {
      router.navigate({ to: '/settings' })
    },
  },
]
