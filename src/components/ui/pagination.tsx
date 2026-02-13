import * as React from 'react'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  MoreHorizontalIcon,
} from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

type PaginationProps = Omit<React.ComponentProps<'nav'>, 'aria-label'> & {
  ariaLabel?: string
}

function Pagination({
  className,
  ariaLabel = 'pagination',
  ...props
}: PaginationProps) {
  return (
    <nav
      role="navigation"
      aria-label={ariaLabel}
      data-slot="pagination"
      className={cn('mx-auto flex w-full justify-center', className)}
      {...props}
    />
  )
}

function PaginationContent({
  className,
  ...props
}: React.ComponentProps<'ul'>) {
  return (
    <ul
      data-slot="pagination-content"
      className={cn('flex items-center gap-0.5', className)}
      {...props}
    />
  )
}

function PaginationItem({ ...props }: React.ComponentProps<'li'>) {
  return <li data-slot="pagination-item" {...props} />
}

type PaginationLinkProps = {
  isActive?: boolean
} & Pick<React.ComponentProps<typeof Button>, 'size' | 'disabled'> &
  React.ComponentProps<'button'>

function PaginationLink({
  className,
  isActive,
  size = 'icon',
  ...props
}: PaginationLinkProps) {
  return (
    <Button
      variant={isActive ? 'outline' : 'ghost'}
      size={size}
      aria-current={isActive ? 'page' : undefined}
      data-slot="pagination-link"
      data-active={isActive}
      className={cn(className)}
      {...props}
    />
  )
}

function PaginationPrevious({
  className,
  text = 'Previous',
  ariaLabel = 'Go to previous page',
  ...props
}: React.ComponentProps<typeof PaginationLink> & {
  text?: string
  ariaLabel?: string
}) {
  return (
    <PaginationLink
      aria-label={ariaLabel}
      size="default"
      className={cn('ps-1.5!', className)}
      {...props}
    >
      <ChevronLeftIcon data-icon="inline-start" className="rtl:rotate-180" />
      <span className="hidden sm:block">{text}</span>
    </PaginationLink>
  )
}

function PaginationNext({
  className,
  text = 'Next',
  ariaLabel = 'Go to next page',
  ...props
}: React.ComponentProps<typeof PaginationLink> & {
  text?: string
  ariaLabel?: string
}) {
  return (
    <PaginationLink
      aria-label={ariaLabel}
      size="default"
      className={cn('pe-1.5!', className)}
      {...props}
    >
      <span className="hidden sm:block">{text}</span>
      <ChevronRightIcon data-icon="inline-end" className="rtl:rotate-180" />
    </PaginationLink>
  )
}

function PaginationEllipsis({
  className,
  moreLabel = 'More pages',
  ...props
}: React.ComponentProps<'span'> & { moreLabel?: string }) {
  return (
    <span
      aria-hidden
      data-slot="pagination-ellipsis"
      className={cn(
        "flex size-8 items-center justify-center [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    >
      <MoreHorizontalIcon />
      <span className="sr-only">{moreLabel}</span>
    </span>
  )
}

export {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
}
