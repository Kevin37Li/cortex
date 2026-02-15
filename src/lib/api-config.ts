import { logger } from '@/lib/logger'

export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8742'

interface ApiResponseBody {
  error?: unknown
  message?: unknown
  detail?: { msg: string; loc?: unknown[]; type?: string }[]
}

interface ApiFetchJsonOptions extends RequestInit {
  expect?: 'json'
}

interface ApiFetchNoBodyOptions extends RequestInit {
  expect: 'none'
}

interface ApiRequestErrorInit {
  message: string
  status: number
  path: string
  code?: string | null
}

export class ApiRequestError extends Error {
  readonly status: number
  readonly path: string
  readonly code: string | null

  constructor({ message, status, path, code }: ApiRequestErrorInit) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
    this.path = path
    this.code = code ?? null
  }
}

async function parseErrorBody(
  response: Response
): Promise<ApiResponseBody | null> {
  try {
    return (await response.json()) as ApiResponseBody
  } catch {
    return null
  }
}

function extractErrorMessage(
  errorBody: ApiResponseBody | null,
  status: number
): string {
  if (typeof errorBody?.message === 'string') {
    return errorBody.message
  }

  if (Array.isArray(errorBody?.detail)) {
    return errorBody.detail.map(d => d.msg).join('; ')
  }

  return `API request failed (${status})`
}

export async function apiFetch<T>(
  path: string,
  options?: ApiFetchJsonOptions
): Promise<T>
export async function apiFetch(
  path: string,
  options: ApiFetchNoBodyOptions
): Promise<void>
export async function apiFetch<T>(
  path: string,
  options?: ApiFetchJsonOptions | ApiFetchNoBodyOptions
): Promise<T | void> {
  const { expect = 'json', ...init } = options ?? {}

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, init)
  } catch (error) {
    logger.error('Network request failed', { path, error })
    throw new Error('Network request failed')
  }

  if (!response.ok) {
    const errorBody = await parseErrorBody(response)
    const message = extractErrorMessage(errorBody, response.status)
    const errorCode =
      typeof errorBody?.error === 'string' ? errorBody.error : null

    logger.error('API request failed', {
      path,
      status: response.status,
      error: errorBody?.error,
      message,
    })
    throw new ApiRequestError({
      message,
      status: response.status,
      path,
      code: errorCode,
    })
  }

  if (expect === 'none' || response.status === 204) {
    return undefined
  }

  try {
    return (await response.json()) as T
  } catch (error) {
    logger.error('Failed to parse API response', {
      path,
      status: response.status,
      error,
    })
    throw new Error('Invalid API response')
  }
}
