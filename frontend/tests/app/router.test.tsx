import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { routes } from '@/app/routes'

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return render(<RouterProvider router={router} />)
}

describe('AppRouter', () => {
  it('redirects the default route to /bondlens', async () => {
    renderAt('/')

    expect(
      await screen.findByRole('heading', { name: /MSC\s+2019-L3/i }),
    ).toBeInTheDocument()
  })

  it('renders the BondLens page at /bondlens', async () => {
    renderAt('/bondlens')

    expect(
      await screen.findByRole('heading', { name: /MSC\s+2019-L3/i }),
    ).toBeInTheDocument()
  })
})
