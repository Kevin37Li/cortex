import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@/test/test-utils'
import type { ProcessingStatus } from '@/services/items'
import { ProcessingStatusBadge } from './ProcessingStatusBadge'

describe('ProcessingStatusBadge', () => {
  it.each<[ProcessingStatus, string]>([
    ['pending', 'Pending'],
    ['processing', 'Processing'],
    ['completed', 'Completed'],
    ['failed', 'Failed'],
  ])('renders %s label', async (status, expectedLabel) => {
    render(<ProcessingStatusBadge status={status} />)

    await waitFor(() => {
      expect(screen.getByText(expectedLabel)).toBeInTheDocument()
    })
  })

  it('shows animated processing indicator', async () => {
    render(<ProcessingStatusBadge status="processing" />)

    await waitFor(() => {
      expect(screen.getByText('Processing')).toBeInTheDocument()
    })

    const badge = screen.getByText('Processing').closest('[data-slot="badge"]')
    expect(badge).toHaveClass('animate-pulse')
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders retry affordance for failed status when callback is provided', async () => {
    const onRetry = vi.fn()
    render(<ProcessingStatusBadge status="failed" onRetry={onRetry} />)

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Retry Processing' })
      ).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Retry Processing' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('does not render retry affordance when callback is not provided', async () => {
    render(<ProcessingStatusBadge status="failed" />)

    await waitFor(() => {
      expect(screen.getByText('Failed')).toBeInTheDocument()
    })
    expect(
      screen.queryByRole('button', { name: 'Retry Processing' })
    ).not.toBeInTheDocument()
  })
})
