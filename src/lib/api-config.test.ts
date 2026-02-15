import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/logger', () => ({
  logger: {
    trace: vi.fn(),
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}))

const { apiFetch } = await import('./api-config')
const { logger } = await import('@/lib/logger')

const fetchMock = vi.fn()

function createMockResponse({
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

describe('apiFetch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  it('throws a network error when fetch rejects', async () => {
    fetchMock.mockRejectedValue(new Error('connect failure'))

    await expect(apiFetch('/api/items/')).rejects.toThrow(
      'Network request failed'
    )
    expect(logger.error).toHaveBeenCalledWith(
      'Network request failed',
      expect.objectContaining({ path: '/api/items/' })
    )
  })

  it('falls back to status message when error response body is not json', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({
        status: 500,
        json: vi.fn().mockRejectedValue(new Error('not json')),
      })
    )

    await expect(apiFetch('/api/items/')).rejects.toThrow(
      'API request failed (500)'
    )
    expect(logger.error).toHaveBeenCalledWith(
      'API request failed',
      expect.objectContaining({
        path: '/api/items/',
        status: 500,
        message: 'API request failed (500)',
      })
    )
  })

  it('extracts and joins detail array messages from FastAPI errors', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({
        status: 422,
        body: {
          detail: [{ msg: 'first validation error' }, { msg: 'second error' }],
        },
      })
    )

    await expect(apiFetch('/api/items/')).rejects.toThrow(
      'first validation error; second error'
    )
  })

  it('throws ApiRequestError with status and code metadata for backend errors', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({
        status: 404,
        body: {
          error: 'item_not_found',
          message: 'Item not found: item-1',
        },
      })
    )

    await expect(apiFetch('/api/items/item-1')).rejects.toMatchObject({
      name: 'ApiRequestError',
      message: 'Item not found: item-1',
      status: 404,
      code: 'item_not_found',
      path: '/api/items/item-1',
    })
  })

  it('throws invalid response when success body json parsing fails', async () => {
    fetchMock.mockResolvedValue(
      createMockResponse({
        status: 200,
        json: vi.fn().mockRejectedValue(new Error('invalid json')),
      })
    )

    await expect(apiFetch('/api/items/')).rejects.toThrow(
      'Invalid API response'
    )
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to parse API response',
      expect.objectContaining({
        path: '/api/items/',
        status: 200,
      })
    )
  })
})
