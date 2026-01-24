import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/items')({
  component: ItemsLayout,
})

function ItemsLayout() {
  return <Outlet />
}
