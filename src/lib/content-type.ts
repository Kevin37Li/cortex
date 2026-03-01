import { File, FileText, Globe, type LucideIcon } from 'lucide-react'
import type { ContentType } from '@/services/items'

export const contentTypeConfig: Record<
  ContentType,
  { icon: LucideIcon; labelKey: string }
> = {
  webpage: {
    icon: Globe,
    labelKey: 'items.contentType.webpage',
  },
  note: {
    icon: FileText,
    labelKey: 'items.contentType.note',
  },
  file: {
    icon: File,
    labelKey: 'items.contentType.file',
  },
}
