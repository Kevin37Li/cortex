import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import { vi } from 'vitest'

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

export function createWrapper(queryClient: QueryClient) {
  function TestQueryClientProvider({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }

  TestQueryClientProvider.displayName = 'TestQueryClientProvider'

  return TestQueryClientProvider
}

export function createMockResponse({
  ok,
  status = 200,
  body,
  json,
}: {
  ok?: boolean
  status?: number
  body?: unknown
  json?: () => Promise<unknown>
}): Response {
  return {
    ok: ok ?? (status >= 200 && status < 300),
    status,
    json: json ?? vi.fn().mockResolvedValue(body),
    headers: new Headers(),
  } as Response
}
