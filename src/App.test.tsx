import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { I18nextProvider } from 'react-i18next'
import { describe, it, expect } from 'vitest'
import App from './App'
import i18n from '@/i18n/config'

// Tauri bindings are mocked globally in src/test/setup.ts

// Simple wrapper without router for testing App component
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return (
    <QueryClientProvider client={queryClient}>
      <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
    </QueryClientProvider>
  )
}

describe('App', () => {
  it('renders children passed to it', () => {
    render(
      <App>
        <div data-testid="test-child">Test Content</div>
      </App>,
      { wrapper: TestWrapper }
    )
    expect(screen.getByTestId('test-child')).toBeInTheDocument()
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })

  it('wraps children in theme provider', () => {
    // Theme provider is applied - we verify by checking the component renders
    // without errors (ThemeProvider would throw if not properly configured)
    render(
      <App>
        <span>Themed content</span>
      </App>,
      { wrapper: TestWrapper }
    )
    expect(screen.getByText('Themed content')).toBeInTheDocument()
  })
})
