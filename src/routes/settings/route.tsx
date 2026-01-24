import { createFileRoute, redirect } from '@tanstack/react-router'
import { useUIStore } from '@/store/ui-store'

export const Route = createFileRoute('/settings')({
  beforeLoad: () => {
    useUIStore.getState().setPreferencesOpen(true)
    throw redirect({ to: '/items', replace: true })
  },
})
