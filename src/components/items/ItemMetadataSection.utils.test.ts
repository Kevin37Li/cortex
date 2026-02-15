import { describe, expect, it } from 'vitest'
import type { Item } from '@/services/items'
import { parseItemMetadata } from './ItemMetadataSection.utils'

describe('parseItemMetadata', () => {
  it('returns normalized metadata fields', () => {
    const parsed = parseItemMetadata({
      summary: 'Summary text',
      concepts: ['AI', 'Knowledge'],
      entities: ['Cortex'],
      processing_error: 'Timed out',
      error_step: 'validating',
    })

    expect(parsed).toEqual({
      summary: 'Summary text',
      concepts: ['AI', 'Knowledge'],
      entities: ['Cortex'],
      processingError: 'Timed out',
      errorStep: 'validating',
    })
  })

  it('filters invalid values to safe defaults', () => {
    const parsed = parseItemMetadata({
      summary: '   ',
      concepts: ['AI', '', 123, null],
      entities: 'not-a-list',
      processing_error: 404,
      error_step: ['bad'],
    } as unknown as Item['metadata'])

    expect(parsed).toEqual({
      summary: null,
      concepts: ['AI'],
      entities: [],
      processingError: null,
      errorStep: null,
    })
  })

  it('returns null for missing or non-object metadata', () => {
    expect(parseItemMetadata(null)).toBeNull()
    expect(parseItemMetadata([] as unknown as Item['metadata'])).toBeNull()
  })
})
