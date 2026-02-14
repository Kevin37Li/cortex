import type { TFunction } from 'i18next'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ImportFileOptions } from './import-file'

vi.mock('@/lib/logger', () => ({
  logger: {
    trace: vi.fn(),
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}))

const { logger } = await import('@/lib/logger')
const { FILE_IMPORT_MAX_SIZE_BYTES, getDefaultImportTitle, importFile } =
  await import('./import-file')

const loggerErrorMock = vi.mocked(logger.error)

function createTranslator(): TFunction {
  return ((key: string, options?: Record<string, unknown>) => {
    switch (key) {
      case 'items.import.title':
        return 'Import File'
      case 'items.import.selectFile':
        return 'Select a file to import'
      case 'items.import.success':
        return 'File imported successfully'
      case 'items.import.error':
        return 'Failed to import file'
      case 'items.import.readError':
        return 'Could not read file'
      case 'items.import.fileTooLarge':
        return `File is too large (max ${String(options?.maxSize ?? '')})`
      default:
        return key
    }
  }) as TFunction
}

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

function toOpenDialogMock(fn: () => Promise<string | string[] | null>) {
  return fn as unknown as NonNullable<ImportFileOptions['openDialog']>
}

function toStatFileMock(fn: (path: string) => Promise<unknown>) {
  return fn as unknown as NonNullable<ImportFileOptions['statFile']>
}

function toReadTextFileMock(fn: (path: string) => Promise<string>) {
  return fn as unknown as NonNullable<ImportFileOptions['readTextFileFn']>
}

describe('getDefaultImportTitle', () => {
  it('strips extension for POSIX and Windows paths', () => {
    expect(getDefaultImportTitle('/Users/me/notes/roadmap.markdown')).toBe(
      'roadmap'
    )
    expect(
      getDefaultImportTitle('C:\\Users\\me\\Desktop\\meeting-notes.md')
    ).toBe('meeting-notes')
  })

  it('keeps filename when there is no extension', () => {
    expect(getDefaultImportTitle('/tmp/README')).toBe('README')
  })
})

describe('importFile', () => {
  beforeEach(() => {
    loggerErrorMock.mockReset()
  })

  it('shows generic error when opening the file dialog fails', async () => {
    const createItem = vi.fn()
    const notifySuccess = vi.fn()
    const notifyError = vi.fn()
    const statFile = vi.fn()
    const readTextFileFn = vi.fn()

    const result = await importFile({
      createItem,
      t: createTranslator(),
      openDialog: toOpenDialogMock(async () => {
        throw new Error('dialog unavailable')
      }),
      statFile: toStatFileMock(statFile),
      readTextFileFn: toReadTextFileMock(readTextFileFn),
      notifySuccess,
      notifyError,
    })

    expect(result).toEqual({ status: 'failed' })
    expect(statFile).not.toHaveBeenCalled()
    expect(readTextFileFn).not.toHaveBeenCalled()
    expect(createItem).not.toHaveBeenCalled()
    expect(notifySuccess).not.toHaveBeenCalled()
    expect(notifyError).toHaveBeenCalledWith('Failed to import file')
    expect(loggerErrorMock).toHaveBeenCalledWith(
      'Failed to open file import dialog',
      expect.objectContaining({
        error: expect.any(Error),
      })
    )
  })

  it('returns cancelled when user closes dialog', async () => {
    const createItem = vi.fn()
    const notifySuccess = vi.fn()
    const notifyError = vi.fn()

    const result = await importFile({
      createItem,
      t: createTranslator(),
      openDialog: toOpenDialogMock(async () => null),
      statFile: toStatFileMock(async () => createFileInfo(256)),
      readTextFileFn: toReadTextFileMock(async () => 'unused'),
      notifySuccess,
      notifyError,
    })

    expect(result).toEqual({ status: 'cancelled' })
    expect(createItem).not.toHaveBeenCalled()
    expect(notifySuccess).not.toHaveBeenCalled()
    expect(notifyError).not.toHaveBeenCalled()
  })

  it('imports a selected file and creates a file item', async () => {
    const createItem = vi.fn().mockResolvedValue({ id: 'item-1' })
    const notifySuccess = vi.fn()
    const notifyError = vi.fn()
    const openDialog = vi
      .fn()
      .mockResolvedValue('C:\\Users\\me\\Desktop\\design-doc.markdown')

    const result = await importFile({
      createItem,
      t: createTranslator(),
      openDialog: toOpenDialogMock(openDialog),
      statFile: toStatFileMock(async () => createFileInfo(256)),
      readTextFileFn: toReadTextFileMock(async () => '# Design Doc'),
      notifySuccess,
      notifyError,
    })

    expect(result).toEqual({ status: 'imported' })
    expect(openDialog).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Import File',
        filters: [
          {
            name: 'Select a file to import',
            extensions: ['txt', 'md', 'markdown'],
          },
        ],
      })
    )
    expect(createItem).toHaveBeenCalledWith({
      title: 'design-doc',
      content: '# Design Doc',
      content_type: 'file',
      source_url: null,
      metadata: null,
    })
    expect(notifySuccess).toHaveBeenCalledWith('File imported successfully')
    expect(notifyError).not.toHaveBeenCalled()
  })

  it('shows file-size error and stops before reading content', async () => {
    const createItem = vi.fn()
    const notifySuccess = vi.fn()
    const notifyError = vi.fn()
    const readTextFileFn = vi.fn()

    const result = await importFile({
      createItem,
      t: createTranslator(),
      openDialog: toOpenDialogMock(async () => '/tmp/too-large.txt'),
      statFile: toStatFileMock(async () =>
        createFileInfo(FILE_IMPORT_MAX_SIZE_BYTES + 1)
      ),
      readTextFileFn: toReadTextFileMock(readTextFileFn),
      notifySuccess,
      notifyError,
    })

    expect(result).toEqual({ status: 'failed' })
    expect(readTextFileFn).not.toHaveBeenCalled()
    expect(createItem).not.toHaveBeenCalled()
    expect(notifySuccess).not.toHaveBeenCalled()
    expect(notifyError).toHaveBeenCalledWith('File is too large (max 5 MB)')
  })

  it('shows generic error when reading file metadata fails', async () => {
    const createItem = vi.fn()
    const notifySuccess = vi.fn()
    const notifyError = vi.fn()
    const readTextFileFn = vi.fn()

    const result = await importFile({
      createItem,
      t: createTranslator(),
      openDialog: toOpenDialogMock(async () => '/tmp/missing.md'),
      statFile: toStatFileMock(async () => {
        throw new Error('metadata denied')
      }),
      readTextFileFn: toReadTextFileMock(readTextFileFn),
      notifySuccess,
      notifyError,
    })

    expect(result).toEqual({ status: 'failed' })
    expect(readTextFileFn).not.toHaveBeenCalled()
    expect(createItem).not.toHaveBeenCalled()
    expect(notifySuccess).not.toHaveBeenCalled()
    expect(notifyError).toHaveBeenCalledWith('Failed to import file')
    expect(loggerErrorMock).toHaveBeenCalledWith(
      'Failed to read file metadata for import',
      expect.objectContaining({ path: '/tmp/missing.md' })
    )
  })

  it('shows read error notification when file read fails', async () => {
    const createItem = vi.fn()
    const notifySuccess = vi.fn()
    const notifyError = vi.fn()

    const result = await importFile({
      createItem,
      t: createTranslator(),
      openDialog: toOpenDialogMock(async () => '/tmp/corrupt.md'),
      statFile: toStatFileMock(async () => createFileInfo(512)),
      readTextFileFn: toReadTextFileMock(async () => {
        throw new Error('cannot read file')
      }),
      notifySuccess,
      notifyError,
    })

    expect(result).toEqual({ status: 'failed' })
    expect(createItem).not.toHaveBeenCalled()
    expect(notifySuccess).not.toHaveBeenCalled()
    expect(notifyError).toHaveBeenCalledWith('Could not read file')
    expect(loggerErrorMock).toHaveBeenCalledWith(
      'Failed to read selected import file',
      expect.objectContaining({ path: '/tmp/corrupt.md' })
    )
  })

  it('shows generic import error when item creation fails', async () => {
    const notifySuccess = vi.fn()
    const notifyError = vi.fn()
    const createItem = vi.fn().mockRejectedValue(new Error('backend down'))

    const result = await importFile({
      createItem,
      t: createTranslator(),
      openDialog: toOpenDialogMock(async () => '/tmp/notes.txt'),
      statFile: toStatFileMock(async () => createFileInfo(128)),
      readTextFileFn: toReadTextFileMock(async () => 'hello'),
      notifySuccess,
      notifyError,
    })

    expect(result).toEqual({ status: 'failed' })
    expect(notifySuccess).not.toHaveBeenCalled()
    expect(notifyError).toHaveBeenCalledWith('Failed to import file')
    expect(loggerErrorMock).toHaveBeenCalledWith(
      'Failed to create imported file item',
      expect.objectContaining({ path: '/tmp/notes.txt' })
    )
  })
})
