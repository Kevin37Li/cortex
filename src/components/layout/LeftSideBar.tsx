import { Link, useRouterState } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { FileText, MessageSquare, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
  path: '/items' | '/conversations'
  labelKey: string
  icon: LucideIcon
}

const navItems: NavItem[] = [
  { path: '/items', labelKey: 'nav.allItems', icon: FileText },
  {
    path: '/conversations',
    labelKey: 'nav.conversations',
    icon: MessageSquare,
  },
]

interface LeftSideBarProps {
  children?: React.ReactNode
  className?: string
}

export function LeftSideBar({ children, className }: LeftSideBarProps) {
  const { t } = useTranslation()
  const routerState = useRouterState()
  const currentPath = routerState.location.pathname

  return (
    <div
      className={cn('flex h-full flex-col border-e bg-background', className)}
    >
      <nav className="flex flex-col gap-1 p-2">
        {navItems.map(item => {
          const Icon = item.icon
          const isActive =
            currentPath === item.path || currentPath.startsWith(`${item.path}/`)

          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                'hover:bg-accent hover:text-accent-foreground',
                isActive &&
                  'bg-accent text-accent-foreground border-e-2 border-primary'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{t(item.labelKey)}</span>
            </Link>
          )
        })}
      </nav>
      {children && <div className="flex-1">{children}</div>}
    </div>
  )
}
