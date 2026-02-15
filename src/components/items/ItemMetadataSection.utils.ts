import type { Item, ItemMetadata } from '@/services/items'

function getNonEmptyString(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value : null
}

function getNonEmptyStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }

  return value.filter((entry): entry is string => {
    return typeof entry === 'string' && entry.trim().length > 0
  })
}

function getMetadataObject(metadata: Item['metadata']): ItemMetadata | null {
  if (
    metadata === null ||
    Array.isArray(metadata) ||
    typeof metadata !== 'object'
  ) {
    return null
  }

  return metadata
}

export interface ParsedItemMetadata {
  summary: string | null
  concepts: string[]
  entities: string[]
  processingError: string | null
  errorStep: string | null
}

export function parseItemMetadata(
  metadata: Item['metadata']
): ParsedItemMetadata | null {
  const metadataObject = getMetadataObject(metadata)
  if (!metadataObject) {
    return null
  }

  return {
    summary: getNonEmptyString(metadataObject.summary),
    concepts: getNonEmptyStringList(metadataObject.concepts),
    entities: getNonEmptyStringList(metadataObject.entities),
    processingError: getNonEmptyString(metadataObject.processing_error),
    errorStep: getNonEmptyString(metadataObject.error_step),
  }
}
