import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { ProcessingUpdate } from '@/types/processing'

interface ProcessingState {
  processingByItemId: Record<string, ProcessingUpdate>
  subscriptionItemId: string | null
  setUpdate: (update: ProcessingUpdate) => void
  removeItem: (itemId: string) => void
  clearProcessingEntries: () => void
  reset: () => void
  setSubscriptionItemId: (itemId: string | null) => void
}

const initialState = {
  processingByItemId: {},
  subscriptionItemId: null,
}

export const useProcessingStore = create<ProcessingState>()(
  devtools(
    set => ({
      ...initialState,
      setUpdate: update =>
        set(
          state => ({
            processingByItemId: {
              ...state.processingByItemId,
              [update.item_id]: update,
            },
          }),
          undefined,
          'setUpdate'
        ),
      removeItem: itemId =>
        set(
          state => {
            const { [itemId]: _removed, ...rest } = state.processingByItemId
            return { processingByItemId: rest }
          },
          undefined,
          'removeItem'
        ),
      clearProcessingEntries: () =>
        set({ processingByItemId: {} }, undefined, 'clearProcessingEntries'),
      reset: () =>
        set(
          {
            ...initialState,
          },
          undefined,
          'reset'
        ),
      setSubscriptionItemId: itemId =>
        set({ subscriptionItemId: itemId }, undefined, 'setSubscriptionItemId'),
    }),
    { name: 'processing-store' }
  )
)
