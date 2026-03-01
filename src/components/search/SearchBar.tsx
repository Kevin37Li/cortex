import { useEffect, useRef } from 'react'
import { Search, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { useUIStore } from '@/store/ui-store'

interface SearchBarProps {
  value: string
  onValueChange: (value: string) => void
  className?: string
}

export function SearchBar({ value, onValueChange, className }: SearchBarProps) {
  const { t } = useTranslation()
  const inputRef = useRef<HTMLInputElement>(null)
  const searchFocused = useUIStore(state => state.searchFocused)
  const hasValue = value.length > 0

  useEffect(() => {
    if (!searchFocused || !inputRef.current) {
      return
    }

    inputRef.current.focus()
    useUIStore.getState().setSearchFocused(false)
  }, [searchFocused])

  return (
    <div className={cn('relative', className)}>
      <Search
        className="pointer-events-none absolute inset-y-0 start-2.5 my-auto size-4 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        ref={inputRef}
        type="search"
        role="searchbox"
        aria-label={t('search.ariaLabel')}
        placeholder={t('search.placeholder')}
        value={value}
        onChange={event => onValueChange(event.target.value)}
        className={cn('ps-8', hasValue && 'pe-8')}
      />
      {hasValue ? (
        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          className="absolute inset-y-0 end-1 my-auto"
          aria-label={t('search.clear')}
          onClick={() => {
            onValueChange('')
            inputRef.current?.focus()
          }}
        >
          <X className="size-3.5" aria-hidden="true" />
        </Button>
      ) : null}
    </div>
  )
}
