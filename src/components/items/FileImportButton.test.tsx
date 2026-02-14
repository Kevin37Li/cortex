import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@/test/test-utils'
import i18n from '@/i18n/config'
import { FileImportButton } from './FileImportButton'

vi.mock('@/services/items', async () => {
  const actual = await vi.importActual('@/services/items')

  return {
    ...actual,
    useCreateItem: vi.fn(),
  }
})

vi.mock('@/lib/notifications', () => ({
  notifications: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/lib/logger', () => ({
  logger: {
    trace: vi.fn(),
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}))

const { useCreateItem } = await import('@/services/items')
const { notifications } = await import('@/lib/notifications')
const { logger } = await import('@/lib/logger')
const { open } = await import('@tauri-apps/plugin-dialog')
const { readTextFile, stat } = await import('@tauri-apps/plugin-fs')

const useCreateItemMock = vi.mocked(useCreateItem)
const successMock = vi.mocked(notifications.success)
const errorMock = vi.mocked(notifications.error)
const loggerErrorMock = vi.mocked(logger.error)
const openMock = vi.mocked(open)
const readTextFileMock = vi.mocked(readTextFile)
const statMock = vi.mocked(stat)

const mutateAsync = vi.fn()

function createFileInfo(size: number) {
  return {
    isFile: true,
    isDirectory: false,
    isSymlink: false,
    size,
    mtime: null,
    atime: null,
    birthtime: null,
    readonly: false,
    fileAttributes: null,
    dev: null,
    ino: null,
    mode: null,
    nlink: null,
    uid: null,
    gid: null,
    rdev: null,
    blksize: null,
    blocks: null,
  }
}

describe('FileImportButton', () => {
  beforeEach(async () => {
    mutateAsync.mockReset()
    successMock.mockReset()
    errorMock.mockReset()
    loggerErrorMock.mockReset()
    openMock.mockReset()
    readTextFileMock.mockReset()
    statMock.mockReset()

    openMock.mockResolvedValue(null)
    statMock.mockResolvedValue(createFileInfo(256))
    readTextFileMock.mockResolvedValue('Sample content')
    successMock.mockResolvedValue(undefined)
    errorMock.mockResolvedValue(undefined)

    useCreateItemMock.mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateItem>)

    await i18n.changeLanguage('en')
  })

  it('renders translated button label', () => {
    render(<FileImportButton />)
    return expect(
      screen.findByRole('button', { name: 'Import File' })
    ).resolves.toBeInTheDocument()
  })

  it('opens native file dialog with expected filters', async () => {
    render(<FileImportButton />)
    const button = await screen.findByRole('button', { name: 'Import File' })

    fireEvent.click(button)

    await waitFor(() => {
      expect(openMock).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Import File',
          multiple: false,
          directory: false,
          filters: [
            {
              name: 'Select a file to import',
              extensions: ['txt', 'md', 'markdown'],
            },
          ],
        })
      )
    })
  })

  it('exits cleanly when user cancels dialog', async () => {
    openMock.mockResolvedValue(null)

    render(<FileImportButton />)
    const button = await screen.findByRole('button', { name: 'Import File' })

    fireEvent.click(button)

    await waitFor(() => {
      expect(openMock).toHaveBeenCalledTimes(1)
    })
    expect(mutateAsync).not.toHaveBeenCalled()
    expect(successMock).not.toHaveBeenCalled()
    expect(errorMock).not.toHaveBeenCalled()
  })

  it('imports file content and shows success notification', async () => {
    mutateAsync.mockResolvedValue({
      id: 'item-1',
      title: 'meeting-notes',
      content: '# Notes',
      content_type: 'file',
      source_url: null,
      created_at: '2026-02-14T00:00:00Z',
      updated_at: '2026-02-14T00:00:00Z',
      processing_status: 'completed',
      metadata: null,
    })
    openMock.mockResolvedValue('/tmp/meeting-notes.md')
    readTextFileMock.mockResolvedValue('# Notes')

    render(<FileImportButton />)
    const button = await screen.findByRole('button', { name: 'Import File' })

    fireEvent.click(button)

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        title: 'meeting-notes',
        content: '# Notes',
        content_type: 'file',
        source_url: null,
        metadata: null,
      })
    })
    await waitFor(() => {
      expect(successMock).toHaveBeenCalledWith('File imported successfully')
    })
    expect(errorMock).not.toHaveBeenCalled()
  })

  it('shows read error when file content cannot be loaded', async () => {
    openMock.mockResolvedValue('/tmp/corrupt.md')
    readTextFileMock.mockRejectedValue(new Error('cannot decode'))

    render(<FileImportButton />)
    const button = await screen.findByRole('button', { name: 'Import File' })

    fireEvent.click(button)

    await waitFor(() => {
      expect(errorMock).toHaveBeenCalledWith('Could not read file')
    })
    expect(loggerErrorMock).toHaveBeenCalledWith(
      'Failed to read selected import file',
      expect.objectContaining({ path: '/tmp/corrupt.md' })
    )
    expect(mutateAsync).not.toHaveBeenCalled()
    expect(successMock).not.toHaveBeenCalled()
  })

  it('blocks import when selected file exceeds max size', async () => {
    openMock.mockResolvedValue('/tmp/large.md')
    statMock.mockResolvedValue(createFileInfo(5 * 1024 * 1024 + 1))

    render(<FileImportButton />)
    const button = await screen.findByRole('button', { name: 'Import File' })

    fireEvent.click(button)

    await waitFor(() => {
      expect(errorMock).toHaveBeenCalledWith('File is too large (max 5 MB)')
    })
    expect(readTextFileMock).not.toHaveBeenCalled()
    expect(mutateAsync).not.toHaveBeenCalled()
  })

  it('uses translation keys for non-English locales', async () => {
    await i18n.changeLanguage('zh')

    render(<FileImportButton />)

    await expect(
      screen.findByRole('button', { name: '导入文件' })
    ).resolves.toBeInTheDocument()
  })

  it('shows importing state when mutation is already pending', async () => {
    useCreateItemMock.mockReturnValue({
      mutateAsync,
      isPending: true,
    } as unknown as ReturnType<typeof useCreateItem>)

    render(<FileImportButton />)

    const button = await screen.findByRole('button', { name: 'Importing...' })
    expect(button).toBeDisabled()
    expect(
      screen.getByTestId('file-import-loading-spinner')
    ).toBeInTheDocument()
  })
})
