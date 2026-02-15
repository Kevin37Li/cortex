import type { Item } from '@/services/items'

export function getMetadataRecord(
  metadata: Item['metadata']
): Record<string, unknown> | null {
  if (metadata === null || Array.isArray(metadata)) {
    return null
  }

  return metadata
}

export function getMetadataString(
  metadata: Record<string, unknown>,
  field: string
): string | null {
  const value = metadata[field]
  return typeof value === 'string' && value.trim().length > 0 ? value : null
}

export function getMetadataStringList(
  metadata: Record<string, unknown>,
  field: string
): string[] {
  const value = metadata[field]
  if (!Array.isArray(value)) {
    return []
  }

  return value.filter((entry): entry is string => {
    return typeof entry === 'string' && entry.trim().length > 0
  })
}
