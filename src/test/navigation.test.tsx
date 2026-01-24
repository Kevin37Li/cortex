import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { I18nextProvider } from 'react-i18next'
import {
  RouterProvider,
  createRouter,
  createMemoryHistory,
  createRootRoute,
  createRoute,
} from '@tanstack/react-router'
import { describe, it, expect } from 'vitest'
import i18n from '@/i18n/config'
import { LeftSideBar } from '@/components/layout/LeftSideBar'

// Create a wrapper that properly integrates with TanStack Router
function createTestWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  // Create a router that renders the LeftSideBar in its root
  const rootRoute = createRootRoute({
    component: LeftSideBar,
  })

  const indexRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/',
    component: () => null,
  })

  const itemsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/items',
    component: () => null,
  })

  const conversationsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: '/conversations',
    component: () => null,
  })

  const routeTree = rootRoute.addChildren([
    indexRoute,
    itemsRoute,
    conversationsRoute,
  ])

  const memoryHistory = createMemoryHistory({ initialEntries: ['/items'] })
  const testRouter = createRouter({
    routeTree,
    history: memoryHistory,
  })

  return function TestWrapper() {
    return (
      <QueryClientProvider client={queryClient}>
        <I18nextProvider i18n={i18n}>
          <RouterProvider router={testRouter} />
        </I18nextProvider>
      </QueryClientProvider>
    )
  }
}

describe('LeftSideBar Navigation', () => {
  it('renders navigation links', async () => {
    const TestWrapper = createTestWrapper()
    render(<TestWrapper />)

    // Wait for router to settle
    await waitFor(() => {
      expect(screen.getByText('All Items')).toBeInTheDocument()
    })

    expect(screen.getByText('Conversations')).toBeInTheDocument()
  })

  it('renders navigation links as anchors', async () => {
    const TestWrapper = createTestWrapper()
    render(<TestWrapper />)

    await waitFor(() => {
      const links = screen.getAllByRole('link')
      expect(links.length).toBeGreaterThanOrEqual(2)
    })
  })

  it('applies RTL-compatible border styling', async () => {
    const TestWrapper = createTestWrapper()
    render(<TestWrapper />)

    await waitFor(() => {
      // Find the sidebar container (the div with border-e class)
      const sidebar = document.querySelector('.border-e')
      expect(sidebar).toBeInTheDocument()
    })
  })
})
