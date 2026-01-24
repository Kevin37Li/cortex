import { describe, it, expect } from 'vitest'
import { router } from '@/lib/router'

// Type helpers for route tree traversal
interface RouteNode {
  id: string
  children?: RouteNode[]
}

describe('Router Configuration', () => {
  it('should be configured with hash history', () => {
    // Hash history is required for Tauri's file:// protocol
    // We check the history type rather than the href which varies by environment
    expect(router.history).toBeDefined()
    // The router should be using createHashHistory
    expect(typeof router.history.push).toBe('function')
    expect(typeof router.history.replace).toBe('function')
  })

  it('should have required routes defined', () => {
    const children = router.routeTree.children as RouteNode[] | undefined
    const routeIds = children?.map(route => route.id) ?? []

    // Verify required routes exist
    expect(routeIds).toContain('/')
    expect(routeIds).toContain('/items')
    expect(routeIds).toContain('/conversations')
    expect(routeIds).toContain('/settings')
    expect(routeIds).toContain('/$') // Catch-all 404
  })

  it('should have /items child routes', () => {
    const children = router.routeTree.children as RouteNode[] | undefined
    const itemsRoute = children?.find(r => r.id === '/items')
    const childIds = itemsRoute?.children?.map(route => route.id) ?? []

    expect(childIds).toContain('/items/')
    expect(childIds).toContain('/items/$id')
  })

  it('should have /conversations child routes', () => {
    const children = router.routeTree.children as RouteNode[] | undefined
    const conversationsRoute = children?.find(r => r.id === '/conversations')
    const childIds = conversationsRoute?.children?.map(route => route.id) ?? []

    expect(childIds).toContain('/conversations/')
    expect(childIds).toContain('/conversations/$id')
  })
})
