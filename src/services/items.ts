import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query'
import { apiFetch } from '@/lib/api-config'
import { logger } from '@/lib/logger'
import type { components } from '@/types/api.gen'

// API types generated from backend Pydantic models (via openapi-typescript)
export type Item = components['schemas']['Item']
export type ItemCreate = components['schemas']['ItemCreate']
export type ItemUpdate = components['schemas']['ItemUpdate']
export type ItemListResponse = components['schemas']['ItemListResponse']
export type ContentType = components['schemas']['ContentType']
export type ProcessingStatus = components['schemas']['ProcessingStatus']

// Frontend-only types (not in the API schema)
export interface ItemListParams {
  offset?: number
  limit?: number
}

interface UpdateItemVariables {
  id: string
  data: ItemUpdate
}

export const itemQueryKeys = {
  all: ['items'] as const,
  lists: () => [...itemQueryKeys.all, 'list'] as const,
  list: (params: ItemListParams = {}) =>
    [...itemQueryKeys.lists(), params] as const,
  details: () => [...itemQueryKeys.all, 'detail'] as const,
  detail: (id: string) => [...itemQueryKeys.details(), id] as const,
}

// Collection endpoints use trailing slash to match FastAPI router definition
// (prefix="/items" with route "/"). Omitting the slash causes a 307 redirect.
// Detail endpoints use /items/{id} (no trailing slash) matching route "/{id}".
function buildItemsPath(params?: ItemListParams): string {
  const searchParams = new URLSearchParams()

  if (params?.offset !== undefined) {
    searchParams.set('offset', String(params.offset))
  }

  if (params?.limit !== undefined) {
    searchParams.set('limit', String(params.limit))
  }

  const query = searchParams.toString()
  return query ? `/api/items/?${query}` : '/api/items/'
}

type UseItemsOptions = Pick<
  UseQueryOptions<ItemListResponse>,
  'placeholderData'
>

export function useItems(params?: ItemListParams, options?: UseItemsOptions) {
  return useQuery({
    ...options,
    queryKey: itemQueryKeys.list(params ?? {}),
    queryFn: () => apiFetch<ItemListResponse>(buildItemsPath(params)),
  })
}

export function useItem(id: string) {
  return useQuery({
    queryKey: itemQueryKeys.detail(id),
    queryFn: () => apiFetch<Item>(`/api/items/${encodeURIComponent(id)}`),
    enabled: Boolean(id),
  })
}

export function createItem(data: ItemCreate) {
  return apiFetch<Item>('/api/items/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export function useCreateItem() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() })
    },
    onError: error => {
      logger.error('Failed to create item', { error })
    },
  })
}

export function useUpdateItem() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: UpdateItemVariables) =>
      apiFetch<Item>(`/api/items/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    onSuccess: (_updatedItem, variables) => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() })
      queryClient.invalidateQueries({
        queryKey: itemQueryKeys.detail(variables.id),
      })
    },
    onError: error => {
      logger.error('Failed to update item', { error })
    },
  })
}

export function useDeleteItem() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/items/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        expect: 'none',
      }),
    onSuccess: (_result, deletedItemId) => {
      queryClient.invalidateQueries({ queryKey: itemQueryKeys.lists() })
      queryClient.removeQueries({
        queryKey: itemQueryKeys.detail(deletedItemId),
      })
    },
    onError: error => {
      logger.error('Failed to delete item', { error })
    },
  })
}
