import { useEffect } from 'react'
import { Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { useUIStore } from '@/store/ui-store'

const ITEMS_SEARCH_INPUT_ID = 'items-search-input'

export function ItemsSearchInput() {
  const { t } = useTranslation()
  const searchFocused = useUIStore(state => state.searchFocused)

  useEffect(() => {
    if (!searchFocused) {
      return
    }

    const searchInput = document.getElementById(ITEMS_SEARCH_INPUT_ID)
    if (!(searchInput instanceof HTMLInputElement)) {
      return
    }

    searchInput.focus()
    useUIStore.getState().setSearchFocused(false)
  }, [searchFocused])

  return (
    <div className="relative">
      <Search
        className="pointer-events-none absolute inset-y-0 start-2.5 my-auto size-4 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        id={ITEMS_SEARCH_INPUT_ID}
        type="search"
        aria-label={t('items.search.ariaLabel')}
        placeholder={t('items.search.placeholder')}
        className="ps-8"
      />
    </div>
  )
}
