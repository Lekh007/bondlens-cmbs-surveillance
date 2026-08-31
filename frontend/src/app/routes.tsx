import { Navigate, type RouteObject } from 'react-router-dom'
import { BondLensPage } from '@/features/bondlens/BondLensPage'

// Exported separately from the browser router instance so tests can build a
// createMemoryRouter from the same route definitions.
export const routes: RouteObject[] = [
  { path: '/', element: <Navigate to="/bondlens" replace /> },
  { path: '/bondlens', element: <BondLensPage /> },
]
