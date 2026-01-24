import ReactDOM from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { RouterProvider } from '@tanstack/react-router'
import './i18n'
import App from './App'
import { queryClient } from './lib/query-client'
import { router } from './lib/router'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <QueryClientProvider client={queryClient}>
    <App>
      <RouterProvider router={router} />
    </App>
    <ReactQueryDevtools initialIsOpen={false} />
  </QueryClientProvider>
)
