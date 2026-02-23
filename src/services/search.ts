import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api-config'
import type { components } from '@/types/api.gen'

// API types generated from backend Pydantic models (via openapi-typescript)
export type SearchRequest = components['schemas']['SearchRequest']
export type SearchResponse = components['schemas']['SearchResponse']
export type SearchResultItem = components['schemas']['SearchResultItem']
export type SearchType = SearchRequest['search_type']

// Frontend-only types (not in the API schema)
export interface SearchParams {
  query: string
  search_type?: SearchType
  limit?: number
}

export interface NormalizedSearchParams {
  query: string
  search_type: SearchType
  limit: number
}

export function normalizeSearchParams(
  params: SearchParams
): NormalizedSearchParams {
  return {
    query: params.query.trim(),
    search_type: params.search_type ?? 'hybrid',
    limit: params.limit ?? 20,
  }
}

function searchKeyFromNormalizedParams(params: NormalizedSearchParams) {
  return [...searchQueryKeys.searches(), params] as const
}

export const searchQueryKeys = {
  all: ['search'] as const,
  searches: () => [...searchQueryKeys.all, 'searches'] as const,
  search: (params: SearchParams) =>
    searchKeyFromNormalizedParams(normalizeSearchParams(params)),
}

export function useSearch(params: SearchParams) {
  const normalized = normalizeSearchParams(params)

  return useQuery({
    queryKey: searchKeyFromNormalizedParams(normalized),
    queryFn: () =>
      apiFetch<SearchResponse>('/api/search/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(normalized),
      }),
    enabled: Boolean(normalized.query),
  })
}
