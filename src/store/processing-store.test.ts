import { beforeEach, describe, expect, it } from 'vitest'
import type { ProcessingUpdate } from '@/types/processing'
import { useProcessingStore } from './processing-store'

const baseUpdate: ProcessingUpdate = {
  type: 'processing_update',
  item_id: 'item-1',
  status: 'processing',
  step: 'extracting',
  progress: 0.65,
  message: 'Extracting metadata...',
}

describe('processing-store', () => {
  beforeEach(() => {
    useProcessingStore.getState().reset()
  })

  it('has the expected initial state', () => {
    const state = useProcessingStore.getState()

    expect(state.processingByItemId).toEqual({})
    expect(state.subscriptionItemId).toBeNull()
  })

  it('stores and updates processing entries by item id', () => {
    const { setUpdate } = useProcessingStore.getState()

    setUpdate(baseUpdate)
    expect(useProcessingStore.getState().processingByItemId['item-1']).toEqual(
      baseUpdate
    )

    const completedUpdate: ProcessingUpdate = {
      ...baseUpdate,
      status: 'completed',
      step: 'completed',
      progress: 1,
    }
    setUpdate(completedUpdate)

    expect(useProcessingStore.getState().processingByItemId['item-1']).toEqual(
      completedUpdate
    )
  })

  it('removes a processing entry', () => {
    const { setUpdate, removeItem } = useProcessingStore.getState()

    setUpdate(baseUpdate)
    removeItem(baseUpdate.item_id)

    expect(
      useProcessingStore.getState().processingByItemId[baseUpdate.item_id]
    ).toBeUndefined()
  })

  it('clearProcessingEntries clears entries without affecting subscriptionItemId', () => {
    const { setUpdate, setSubscriptionItemId, clearProcessingEntries } =
      useProcessingStore.getState()

    setUpdate(baseUpdate)
    setSubscriptionItemId('item-42')
    clearProcessingEntries()

    const state = useProcessingStore.getState()
    expect(state.processingByItemId).toEqual({})
    expect(state.subscriptionItemId).toBe('item-42')
  })

  it('reset clears all state including subscriptionItemId', () => {
    const { setSubscriptionItemId, setUpdate, reset } =
      useProcessingStore.getState()

    setUpdate(baseUpdate)
    setSubscriptionItemId('item-42')
    reset()

    const state = useProcessingStore.getState()
    expect(state.processingByItemId).toEqual({})
    expect(state.subscriptionItemId).toBeNull()
  })
})
