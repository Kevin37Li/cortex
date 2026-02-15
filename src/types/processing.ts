import type { components } from '@/types/api.gen'

export type ProcessingStatus = components['schemas']['ProcessingStatus']
export type ProcessingStep = components['schemas']['ProcessingStep']

export interface ProcessingUpdate {
  type: 'processing_update'
  item_id: string
  status: ProcessingStatus
  step: ProcessingStep
  progress: number
  message: string
}

const processingStatuses = [
  'pending',
  'processing',
  'completed',
  'failed',
] as const satisfies readonly ProcessingStatus[]

const processingSteps = [
  'classify',
  'parsing',
  'chunking',
  'extracting',
  'validating',
  'storing',
  'completed',
  'failed',
] as const satisfies readonly ProcessingStep[]

function isProcessingStatus(value: unknown): value is ProcessingStatus {
  return (
    typeof value === 'string' &&
    processingStatuses.includes(value as ProcessingStatus)
  )
}

function isProcessingStep(value: unknown): value is ProcessingStep {
  return (
    typeof value === 'string' &&
    processingSteps.includes(value as ProcessingStep)
  )
}

export function isProcessingUpdate(value: unknown): value is ProcessingUpdate {
  if (!value || typeof value !== 'object') {
    return false
  }

  const update = value as Partial<ProcessingUpdate>

  return (
    update.type === 'processing_update' &&
    typeof update.item_id === 'string' &&
    update.item_id.length > 0 &&
    isProcessingStatus(update.status) &&
    isProcessingStep(update.step) &&
    typeof update.progress === 'number' &&
    Number.isFinite(update.progress) &&
    update.progress >= 0 &&
    update.progress <= 1 &&
    typeof update.message === 'string'
  )
}
