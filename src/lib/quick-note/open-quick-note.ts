import { useUIStore } from '@/store/ui-store'

export function openQuickNoteDialog(): void {
  useUIStore.getState().setQuickNoteDialogOpen(true)
}
