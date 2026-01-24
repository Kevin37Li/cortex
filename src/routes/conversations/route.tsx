import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/conversations')({
  component: ConversationsLayout,
})

function ConversationsLayout() {
  return <Outlet />
}
