import type { TFunction } from 'i18next'
import { open } from '@tauri-apps/plugin-dialog'
import { readTextFile, stat } from '@tauri-apps/plugin-fs'
import i18n from '@/i18n/config'
import { logger } from '@/lib/logger'
import { notifications } from '@/lib/notifications'
import type { ItemCreate } from '@/services/items'

const SUPPORTED_EXTENSIONS = ['txt', 'md', 'markdown']
export const FILE_IMPORT_MAX_SIZE_BYTES = 5 * 1024 * 1024

export interface ImportFileOptions {
  createItem: (data: ItemCreate) => Promise<unknown>
  t?: TFunction
  openDialog?: typeof open
  statFile?: typeof stat
  readTextFileFn?: typeof readTextFile
  notifySuccess?: (title: string) => Promise<void> | void
  notifyError?: (title: string) => Promise<void> | void
  maxFileSizeBytes?: number
}

export type ImportFileStatus = 'imported' | 'cancelled' | 'failed'

export interface ImportFileResult {
  status: ImportFileStatus
}

function getFilenameFromPath(path: string): string {
  const normalized = path.replaceAll('\\', '/')
  const segments = normalized.split('/').filter(Boolean)
  const filename = segments.at(-1)

  return filename ?? path
}

function stripExtension(filename: string): string {
  const extensionIndex = filename.lastIndexOf('.')
  if (extensionIndex <= 0) {
    return filename
  }

  const title = filename.slice(0, extensionIndex).trim()
  return title || filename
}

export function getDefaultImportTitle(path: string): string {
  return stripExtension(getFilenameFromPath(path))
}

function formatMaxSizeLabel(sizeBytes: number): string {
  const megabytes = sizeBytes / (1024 * 1024)
  if (Number.isInteger(megabytes)) {
    return `${megabytes} MB`
  }

  return `${megabytes.toFixed(1)} MB`
}

export async function importFile({
  createItem,
  t = i18n.t.bind(i18n),
  openDialog = open,
  statFile = stat,
  readTextFileFn = readTextFile,
  notifySuccess = notifications.success,
  notifyError = notifications.error,
  maxFileSizeBytes = FILE_IMPORT_MAX_SIZE_BYTES,
}: ImportFileOptions): Promise<ImportFileResult> {
  let selectedPath: string

  try {
    const selected = await openDialog({
      title: t('items.import.title'),
      multiple: false,
      directory: false,
      filters: [
        {
          name: t('items.import.selectFile'),
          extensions: SUPPORTED_EXTENSIONS,
        },
      ],
    })

    if (!selected) {
      return { status: 'cancelled' }
    }

    if (Array.isArray(selected)) {
      logger.warn('File import dialog returned multiple files unexpectedly', {
        count: selected.length,
      })
      return { status: 'cancelled' }
    }

    selectedPath = selected
  } catch (error) {
    logger.error('Failed to open file import dialog', { error })
    await notifyError(t('items.import.error'))
    return { status: 'failed' }
  }

  try {
    const fileInfo = await statFile(selectedPath)
    if (fileInfo.size > maxFileSizeBytes) {
      await notifyError(
        t('items.import.fileTooLarge', {
          maxSize: formatMaxSizeLabel(maxFileSizeBytes),
        })
      )
      return { status: 'failed' }
    }
  } catch (error) {
    logger.error('Failed to read file metadata for import', {
      error,
      path: selectedPath,
    })
    await notifyError(t('items.import.error'))
    return { status: 'failed' }
  }

  let content: string
  try {
    content = await readTextFileFn(selectedPath)
  } catch (error) {
    logger.error('Failed to read selected import file', {
      error,
      path: selectedPath,
    })
    await notifyError(t('items.import.readError'))
    return { status: 'failed' }
  }

  try {
    await createItem({
      title: getDefaultImportTitle(selectedPath),
      content,
      content_type: 'file',
      source_url: null,
      metadata: null,
    })

    await notifySuccess(t('items.import.success'))
    return { status: 'imported' }
  } catch (error) {
    logger.error('Failed to create imported file item', {
      error,
      path: selectedPath,
    })
    await notifyError(t('items.import.error'))
    return { status: 'failed' }
  }
}
