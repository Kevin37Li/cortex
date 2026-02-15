import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import i18n from '@/i18n/config'
import { ItemMetadataSection } from './ItemMetadataSection'

describe('ItemMetadataSection', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders summary, concepts, and entities from metadata', async () => {
    render(
      <ItemMetadataSection
        metadata={{
          summary: 'A compact summary',
          concepts: ['Knowledge Graph', 'Embeddings'],
          entities: ['Cortex', 'SQLite'],
        }}
      />
    )

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'Extracted Metadata' })
      ).toBeInTheDocument()
    })

    expect(screen.getByText('Summary')).toBeInTheDocument()
    expect(screen.getByText('A compact summary')).toBeInTheDocument()
    expect(screen.getByText('Key Concepts')).toBeInTheDocument()
    expect(screen.getByText('Knowledge Graph')).toBeInTheDocument()
    expect(screen.getByText('Embeddings')).toBeInTheDocument()
    expect(screen.getByText('Entities')).toBeInTheDocument()
    expect(screen.getByText('Cortex')).toBeInTheDocument()
    expect(screen.getByText('SQLite')).toBeInTheDocument()
  })

  it('renders nothing when extraction metadata is missing', async () => {
    render(
      <ItemMetadataSection
        metadata={{
          processing_error: 'Parser failed',
          error_step: 'extract',
        }}
      />
    )

    await waitFor(() => {
      expect(
        screen.queryByRole('heading', { name: 'Extracted Metadata' })
      ).not.toBeInTheDocument()
    })
  })
})
