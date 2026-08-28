import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { routes } from '@/app/routes'

// The API base URL points nowhere in tests - BondLensPage's queries fail
// fast (network error) rather than hang, which is what we want here: this
// test only verifies routing, not data loading.
vi.stubGlobal(
  'fetch',
  vi.fn(() => Promise.reject(new Error('network disabled in router test'))),
)

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('AppRouter', () => {
  it('redirects the default route to /bondlens', async () => {
    renderAt('/')

    expect(await screen.findByText(/select or ingest a deal/i)).toBeInTheDocument()
  })

  it('renders the BondLens page at /bondlens', async () => {
    renderAt('/bondlens')

    expect(await screen.findByText(/select or ingest a deal/i)).toBeInTheDocument()
  })
})
