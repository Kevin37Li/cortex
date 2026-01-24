import React, { useState } from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { I18nextProvider } from 'react-i18next'
import {
  RouterProvider,
  createRouter,
  createMemoryHistory,
  createRootRoute,
  createRoute,
} from '@tanstack/react-router'
import i18n from '@/i18n/config'
import {
  ThemeProviderContext,
  type Theme,
  type ThemeProviderState,
} from '@/lib/theme-context'

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  })

interface AllTheProvidersProps {
  children: React.ReactNode
}

/**
 * Mock ThemeProvider for tests that doesn't depend on Tauri or localStorage
 */
function MockThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('light')

  const value: ThemeProviderState = {
    theme,
    setTheme,
  }

  return (
    <ThemeProviderContext.Provider value={value}>
      {children}
    </ThemeProviderContext.Provider>
  )
}

interface AllTheProvidersOptions {
  initialPath?: string
}

function createAllTheProviders(options: AllTheProvidersOptions = {}) {
  const { initialPath = '/' } = options

  return function AllTheProviders({ children }: AllTheProvidersProps) {
    const queryClient = createTestQueryClient()

    // Create router with children as the component to render
    const rootRoute = createRootRoute({
      component: () => <>{children}</>,
    })

    const routeTree = rootRoute.addChildren([
      createRoute({
        getParentRoute: () => rootRoute,
        path: '/',
        component: () => null,
      }),
      createRoute({
        getParentRoute: () => rootRoute,
        path: '/items',
        component: () => null,
      }),
      createRoute({
        getParentRoute: () => rootRoute,
        path: '/conversations',
        component: () => null,
      }),
      createRoute({
        getParentRoute: () => rootRoute,
        path: '$',
        component: () => null,
      }),
    ])

    const memoryHistory = createMemoryHistory({ initialEntries: [initialPath] })
    const testRouter = createRouter({
      routeTree,
      history: memoryHistory,
    })

    return (
      <QueryClientProvider client={queryClient}>
        <I18nextProvider i18n={i18n}>
          <MockThemeProvider>
            <RouterProvider router={testRouter} />
          </MockThemeProvider>
        </I18nextProvider>
      </QueryClientProvider>
    )
  }
}

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialPath?: string
}

const customRender = (
  ui: React.ReactElement,
  options?: CustomRenderOptions
) => {
  const { initialPath, ...renderOptions } = options ?? {}
  const wrapper = createAllTheProviders({ initialPath })
  return render(ui, { wrapper, ...renderOptions })
}

export * from '@testing-library/react'
export { customRender as render }
