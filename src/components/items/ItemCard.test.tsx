import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@/test/test-utils'
import i18n from '@/i18n/config'
import type { Item } from '@/services/items'
import { useProcessingStore } from '@/store/processing-store'
import { ItemCard } from './ItemCard'

const baseItem: Item = {
  id: 'item-1',
  title: 'Example item',
  content: 'Example content',
  content_type: 'note',
  source_url: null,
  created_at: '2026-02-12T10:00:00Z',
  updated_at: '2026-02-12T10:00:00Z',
  processing_status: 'pending',
  metadata: null,
}

describe('ItemCard', () => {
  beforeEach(async () => {
    useProcessingStore.getState().reset()
    await i18n.changeLanguage('en')
    vi.spyOn(Date, 'now').mockReturnValue(
      new Date('2026-02-12T12:00:00Z').getTime()
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders item metadata and typed detail navigation', async () => {
    render(<ItemCard item={baseItem} />, { initialPath: '/items' })

    await waitFor(() => {
      expect(screen.getByText('Example item')).toBeInTheDocument()
    })

    expect(screen.getByText('Note')).toBeInTheDocument()
    expect(screen.getByText('Pending')).toBeInTheDocument()
    expect(screen.getByText('2 hours ago')).toBeInTheDocument()

    const detailLink = screen.getByRole('link', { name: /Example item/i })
    expect(detailLink).toHaveAttribute('href', '/items/item-1')
  })

  it('calls retry callback for failed items', async () => {
    const onRetryProcessing = vi.fn()
    const failedItem: Item = {
      ...baseItem,
      id: 'item-2',
      processing_status: 'failed',
    }

    render(
      <ItemCard item={failedItem} onRetryProcessing={onRetryProcessing} />,
      { initialPath: '/items' }
    )

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Retry Processing' })
      ).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Retry Processing' }))
    expect(onRetryProcessing).toHaveBeenCalledWith(failedItem)
  })

  it('renders translated metadata in Chinese', async () => {
    await i18n.changeLanguage('zh')

    render(<ItemCard item={baseItem} />, { initialPath: '/items' })

    await waitFor(() => {
      expect(screen.getByText('Example item')).toBeInTheDocument()
    })

    expect(screen.getByText('笔记')).toBeInTheDocument()
    expect(screen.getByText('待处理')).toBeInTheDocument()
    expect(screen.getByText(/2.*前/)).toBeInTheDocument()
  })

  it('prefers live processing status and step label from the processing store', async () => {
    useProcessingStore.getState().setUpdate({
      type: 'processing_update',
      item_id: baseItem.id,
      status: 'processing',
      step: 'extracting',
      progress: 0.65,
      message: 'Extracting metadata...',
    })

    render(<ItemCard item={baseItem} />, { initialPath: '/items' })

    await waitFor(() => {
      expect(screen.getByText('Processing')).toBeInTheDocument()
    })

    expect(screen.getByText('Extracting metadata...')).toBeInTheDocument()
  })
})
