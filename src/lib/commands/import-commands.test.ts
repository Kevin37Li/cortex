import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CommandContext } from './types'

vi.mock('@/lib/file-import', () => ({
  importFile: vi.fn(),
}))

vi.mock('@/lib/query-client', () => ({
  queryClient: {
    invalidateQueries: vi.fn(),
  },
}))

vi.mock('@/services/items', async () => {
  const actual = await vi.importActual('@/services/items')

  return {
    ...actual,
    createItem: vi.fn(),
  }
})

const { importCommands } = await import('./import-commands')
const { importFile } = await import('@/lib/file-import')
const { queryClient } = await import('@/lib/query-client')
const { createItem, itemQueryKeys } = await import('@/services/items')

const importFileMock = vi.mocked(importFile)
const createItemMock = vi.mocked(createItem)
const invalidateQueriesMock = vi.mocked(queryClient.invalidateQueries)

function createMockContext(): CommandContext {
  return {
    openPreferences: vi.fn(),
    showToast: vi.fn(),
  }
}

describe('importCommands', () => {
  beforeEach(() => {
    importFileMock.mockReset()
    createItemMock.mockReset()
    invalidateQueriesMock.mockReset()
    invalidateQueriesMock.mockResolvedValue(undefined)
  })

  it('registers import-file command metadata', () => {
    const command = importCommands.find(cmd => cmd.id === 'import-file')

    expect(command).toBeDefined()
    expect(command?.labelKey).toBe('commands.importFile.label')
    expect(command?.descriptionKey).toBe('commands.importFile.description')
    expect(command?.group).toBe('notes')
    expect(command?.keywords).toContain('import')
  })

  it('uses shared import workflow and invalidates item list after create', async () => {
    const command = importCommands.find(cmd => cmd.id === 'import-file')
    expect(command).toBeDefined()

    const importedPayload = {
      title: 'README',
      content: 'Hello',
      content_type: 'file' as const,
      source_url: null,
      metadata: null,
    }

    createItemMock.mockResolvedValue({
      id: 'item-1',
      ...importedPayload,
      created_at: '2026-02-14T00:00:00Z',
      updated_at: '2026-02-14T00:00:00Z',
      processing_status: 'completed',
    })

    importFileMock.mockImplementation(async ({ createItem: runCreateItem }) => {
      await runCreateItem(importedPayload)
      return { status: 'imported' }
    })

    const ctx = createMockContext()
    await command?.execute(ctx)

    expect(ctx.showToast).not.toHaveBeenCalled()
    expect(importFileMock).toHaveBeenCalledTimes(1)
    expect(createItemMock).toHaveBeenCalledWith(importedPayload)
    expect(invalidateQueriesMock).toHaveBeenCalledWith({
      queryKey: itemQueryKeys.lists(),
    })
  })

  it('does not invalidate items when import workflow is cancelled', async () => {
    const command = importCommands.find(cmd => cmd.id === 'import-file')
    expect(command).toBeDefined()

    importFileMock.mockResolvedValue({ status: 'cancelled' })

    await command?.execute(createMockContext())

    expect(importFileMock).toHaveBeenCalledTimes(1)
    expect(createItemMock).not.toHaveBeenCalled()
    expect(invalidateQueriesMock).not.toHaveBeenCalled()
  })

  it('does not invalidate items when import workflow fails before create', async () => {
    const command = importCommands.find(cmd => cmd.id === 'import-file')
    expect(command).toBeDefined()

    importFileMock.mockResolvedValue({ status: 'failed' })

    await command?.execute(createMockContext())

    expect(importFileMock).toHaveBeenCalledTimes(1)
    expect(createItemMock).not.toHaveBeenCalled()
    expect(invalidateQueriesMock).not.toHaveBeenCalled()
  })
})
