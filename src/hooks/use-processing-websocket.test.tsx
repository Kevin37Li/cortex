import { act, render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useProcessingWebSocket } from './use-processing-websocket'
import { itemQueryKeys } from '@/services/items'
import { useProcessingStore } from '@/store/processing-store'
import { logger } from '@/lib/logger'

vi.mock('@/lib/logger', () => ({
  logger: {
    trace: vi.fn(),
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}))

const mockLogger = vi.mocked(logger)

class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  static instances: MockWebSocket[] = []

  readonly url: string
  readyState = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onclose: ((event: Event) => void) | null = null
  sentMessages: string[] = []

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  send = vi.fn((data: string) => {
    this.sentMessages.push(data)
  })

  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new Event('close'))
  })

  triggerOpen() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }

  triggerMessage(data: unknown) {
    this.onmessage?.({
      data: typeof data === 'string' ? data : JSON.stringify(data),
    } as MessageEvent)
  }

  triggerRawMessage(data: unknown) {
    this.onmessage?.({ data } as MessageEvent)
  }

  triggerClose() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new Event('close'))
  }

  static latest(): MockWebSocket {
    const instance = MockWebSocket.instances.at(-1)
    if (!instance) {
      throw new Error('Expected at least one WebSocket instance')
    }
    return instance
  }

  static reset() {
    MockWebSocket.instances = []
  }
}

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function WebSocketHarness() {
  useProcessingWebSocket()
  return null
}

describe('useProcessingWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.reset()
    useProcessingStore.getState().reset()
    vi.clearAllMocks()
    vi.useFakeTimers()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
  })

  afterEach(() => {
    useProcessingStore.getState().reset()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('connects, applies updates, invalidates caches on final states, and clears entries after delay', async () => {
    const queryClient = createTestQueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    render(
      <QueryClientProvider client={queryClient}>
        <WebSocketHarness />
      </QueryClientProvider>
    )

    const ws = MockWebSocket.latest()
    expect(ws.url).toBe('ws://127.0.0.1:8742/api/ws/processing')

    act(() => {
      ws.triggerOpen()
    })
    expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ subscribe: '' }))

    act(() => {
      ws.triggerMessage({
        type: 'processing_update',
        item_id: 'item-1',
        status: 'processing',
        step: 'extracting',
        progress: 0.65,
        message: 'Extracting metadata...',
      })
    })
    expect(
      useProcessingStore.getState().processingByItemId['item-1']
    ).toMatchObject({
      status: 'processing',
      step: 'extracting',
    })

    act(() => {
      ws.triggerMessage({
        type: 'processing_update',
        item_id: 'item-1',
        status: 'completed',
        step: 'completed',
        progress: 1,
        message: 'Completed',
      })
      ws.triggerMessage({
        type: 'processing_update',
        item_id: 'item-2',
        status: 'failed',
        step: 'failed',
        progress: 1,
        message: 'Failed',
      })
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: itemQueryKeys.lists(),
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: itemQueryKeys.detail('item-1'),
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: itemQueryKeys.detail('item-2'),
    })

    act(() => {
      vi.advanceTimersByTime(3000)
    })

    expect(
      useProcessingStore.getState().processingByItemId['item-1']
    ).toBeUndefined()
    expect(
      useProcessingStore.getState().processingByItemId['item-2']
    ).toBeUndefined()
  })

  it('logs a warning for unparseable JSON messages', () => {
    const queryClient = createTestQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <WebSocketHarness />
      </QueryClientProvider>
    )

    const ws = MockWebSocket.latest()
    act(() => {
      ws.triggerOpen()
      ws.triggerMessage('not-json')
    })

    expect(useProcessingStore.getState().processingByItemId).toEqual({})
    expect(mockLogger.warn).toHaveBeenCalledWith(
      'Failed to parse processing WebSocket message',
      expect.objectContaining({ error: expect.any(SyntaxError) })
    )
  })

  it('logs a warning and ignores non-string websocket payloads', () => {
    const queryClient = createTestQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <WebSocketHarness />
      </QueryClientProvider>
    )

    const ws = MockWebSocket.latest()
    act(() => {
      ws.triggerOpen()
      ws.triggerRawMessage({ type: 'processing_update' })
    })

    expect(useProcessingStore.getState().processingByItemId).toEqual({})
    expect(mockLogger.warn).toHaveBeenCalledWith(
      'Processing WebSocket received non-string message, ignoring'
    )
  })

  it('silently ignores valid JSON with invalid processing status', () => {
    const queryClient = createTestQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <WebSocketHarness />
      </QueryClientProvider>
    )

    const ws = MockWebSocket.latest()
    act(() => {
      ws.triggerOpen()
      ws.triggerMessage({
        type: 'processing_update',
        item_id: 'item-1',
        status: 'unknown',
        step: 'extracting',
        progress: 0.5,
        message: 'Invalid status',
      })
    })

    expect(useProcessingStore.getState().processingByItemId).toEqual({})
    expect(mockLogger.warn).not.toHaveBeenCalledWith(
      'Failed to parse processing WebSocket message',
      expect.anything()
    )
  })

  it('clears in-flight entries but preserves terminal entries on disconnect', () => {
    const queryClient = createTestQueryClient()

    render(
      <QueryClientProvider client={queryClient}>
        <WebSocketHarness />
      </QueryClientProvider>
    )

    const ws = MockWebSocket.latest()
    act(() => {
      ws.triggerOpen()
      ws.triggerMessage({
        type: 'processing_update',
        item_id: 'item-1',
        status: 'processing',
        step: 'extracting',
        progress: 0.5,
        message: 'Extracting metadata...',
      })
      ws.triggerMessage({
        type: 'processing_update',
        item_id: 'item-2',
        status: 'completed',
        step: 'completed',
        progress: 1,
        message: 'Completed',
      })
    })

    expect(
      useProcessingStore.getState().processingByItemId['item-1']
    ).toBeDefined()
    expect(
      useProcessingStore.getState().processingByItemId['item-2']
    ).toBeDefined()

    act(() => {
      ws.triggerClose()
    })

    expect(
      useProcessingStore.getState().processingByItemId['item-1']
    ).toBeUndefined()
    expect(
      useProcessingStore.getState().processingByItemId['item-2']
    ).toMatchObject({ status: 'completed' })

    act(() => {
      vi.advanceTimersByTime(2999)
    })
    expect(
      useProcessingStore.getState().processingByItemId['item-2']
    ).toBeDefined()

    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(
      useProcessingStore.getState().processingByItemId['item-2']
    ).toBeUndefined()
  })

  it('reconnects with capped exponential backoff and logs max-attempt exhaustion', () => {
    const queryClient = createTestQueryClient()
    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout')

    render(
      <QueryClientProvider client={queryClient}>
        <WebSocketHarness />
      </QueryClientProvider>
    )

    let ws = MockWebSocket.latest()
    const expectedDelays = [2000, 4000, 8000, 16000, 30000, 30000] as const

    for (const delay of expectedDelays) {
      act(() => {
        ws.triggerClose()
      })
      expect(setTimeoutSpy).toHaveBeenLastCalledWith(
        expect.any(Function),
        delay
      )

      act(() => {
        vi.advanceTimersByTime(delay)
      })
      ws = MockWebSocket.latest()
    }

    for (let i = expectedDelays.length; i < 10; i++) {
      act(() => {
        ws.triggerClose()
      })
      act(() => {
        vi.runOnlyPendingTimers()
      })
      ws = MockWebSocket.latest()
    }

    act(() => {
      ws.triggerClose()
    })

    expect(mockLogger.warn).toHaveBeenCalledWith(
      'Processing WebSocket exhausted reconnect attempts',
      { maxReconnectAttempts: 10 }
    )
  })

  it('syncs subscription updates and reapplies subscription after reconnect', () => {
    const queryClient = createTestQueryClient()
    useProcessingStore.getState().setSubscriptionItemId('item-42')

    const { unmount } = render(
      <QueryClientProvider client={queryClient}>
        <WebSocketHarness />
      </QueryClientProvider>
    )

    const ws1 = MockWebSocket.latest()
    act(() => {
      ws1.triggerOpen()
    })
    expect(ws1.send).toHaveBeenCalledWith(
      JSON.stringify({ subscribe: 'item-42' })
    )

    act(() => {
      useProcessingStore.getState().setSubscriptionItemId('item-9')
    })
    expect(ws1.send).toHaveBeenLastCalledWith(
      JSON.stringify({ subscribe: 'item-9' })
    )

    act(() => {
      ws1.triggerClose()
      vi.advanceTimersByTime(2000)
    })

    const ws2 = MockWebSocket.latest()
    act(() => {
      ws2.triggerOpen()
    })
    expect(ws2.send).toHaveBeenCalledWith(
      JSON.stringify({ subscribe: 'item-9' })
    )

    unmount()
    expect(ws2.close).toHaveBeenCalledTimes(1)
  })
})
