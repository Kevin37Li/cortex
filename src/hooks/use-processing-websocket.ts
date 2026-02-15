import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { API_BASE } from '@/lib/api-config'
import { logger } from '@/lib/logger'
import { itemQueryKeys } from '@/services/items'
import { useProcessingStore } from '@/store/processing-store'
import { isProcessingUpdate } from '@/types/processing'

const MAX_RECONNECT_ATTEMPTS = 10
const RECONNECT_DELAYS_MS = [2000, 4000, 8000, 16000, 30000] as const
const MAX_RECONNECT_DELAY_MS =
  RECONNECT_DELAYS_MS[RECONNECT_DELAYS_MS.length - 1] ?? 30000
const COMPLETED_CLEANUP_DELAY_MS = 3000

function isTerminalStatus(status: string): boolean {
  return status === 'completed' || status === 'failed'
}

function getProcessingWsUrl(): string {
  const url = new URL('/api/ws/processing', API_BASE)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}

function getReconnectDelayMs(attemptIndex: number): number {
  const clamped = Math.max(
    0,
    Math.min(attemptIndex, RECONNECT_DELAYS_MS.length - 1)
  )
  return RECONNECT_DELAYS_MS[clamped] ?? MAX_RECONNECT_DELAY_MS
}

function sendSubscription(ws: WebSocket, itemId: string | null) {
  try {
    ws.send(JSON.stringify({ subscribe: itemId ?? '' }))
  } catch (error) {
    logger.warn('Failed to send processing WebSocket subscription', { error })
  }
}

/**
 * Manages the processing updates websocket connection.
 * Mount once at app root so updates are available to both list and detail views.
 */
export function useProcessingWebSocket() {
  const queryClient = useQueryClient()
  const subscriptionItemId = useProcessingStore(
    state => state.subscriptionItemId
  )
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let disposed = false
    let reconnectAttempts = 0
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    const cleanupTimers = new Map<string, ReturnType<typeof setTimeout>>()

    const clearCleanupTimer = (itemId: string) => {
      const existingTimer = cleanupTimers.get(itemId)
      if (!existingTimer) {
        return
      }
      clearTimeout(existingTimer)
      cleanupTimers.delete(itemId)
    }

    const scheduleReconnect = () => {
      if (disposed || reconnectTimer !== null) {
        return
      }

      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        logger.warn('Processing WebSocket exhausted reconnect attempts', {
          maxReconnectAttempts: MAX_RECONNECT_ATTEMPTS,
        })
        return
      }

      const attempt = reconnectAttempts + 1
      const delayMs = getReconnectDelayMs(reconnectAttempts)
      reconnectAttempts = attempt

      logger.warn('Processing WebSocket reconnect scheduled', {
        attempt,
        maxReconnectAttempts: MAX_RECONNECT_ATTEMPTS,
        delayMs,
      })

      reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        connect()
      }, delayMs)
    }

    const connect = () => {
      if (disposed) {
        return
      }

      const ws = new WebSocket(getProcessingWsUrl())
      wsRef.current = ws

      ws.onopen = () => {
        logger.debug('Processing WebSocket connected')
        reconnectAttempts = 0
        sendSubscription(ws, useProcessingStore.getState().subscriptionItemId)
      }

      ws.onmessage = event => {
        if (typeof event.data !== 'string') {
          logger.warn(
            'Processing WebSocket received non-string message, ignoring'
          )
          return
        }

        let parsedData: unknown
        try {
          parsedData = JSON.parse(event.data)
        } catch (error) {
          logger.warn('Failed to parse processing WebSocket message', { error })
          return
        }

        if (!isProcessingUpdate(parsedData)) {
          return
        }

        const update = parsedData
        useProcessingStore.getState().setUpdate(update)

        clearCleanupTimer(update.item_id)

        if (update.status === 'completed' || update.status === 'failed') {
          queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() })
          queryClient.invalidateQueries({
            queryKey: itemQueryKeys.detail(update.item_id),
          })

          const timer = setTimeout(() => {
            useProcessingStore.getState().removeItem(update.item_id)
            cleanupTimers.delete(update.item_id)
          }, COMPLETED_CLEANUP_DELAY_MS)
          cleanupTimers.set(update.item_id, timer)
        }
      }

      ws.onerror = event => {
        logger.error('Processing WebSocket error', { event })
      }

      ws.onclose = () => {
        logger.warn('Processing WebSocket disconnected')
        const { processingByItemId, removeItem } = useProcessingStore.getState()
        for (const [itemId, update] of Object.entries(processingByItemId)) {
          if (!isTerminalStatus(update.status)) {
            removeItem(itemId)
          }
        }
        scheduleReconnect()
      }
    }

    connect()

    return () => {
      disposed = true
      if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer)
      }
      for (const timer of cleanupTimers.values()) {
        clearTimeout(timer)
      }
      cleanupTimers.clear()
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [queryClient])

  useEffect(() => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return
    }

    sendSubscription(ws, subscriptionItemId)
  }, [subscriptionItemId])
}
