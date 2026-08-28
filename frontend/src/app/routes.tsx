import { Navigate, type RouteObject } from 'react-router-dom'
import { BondLensPage } from '@/features/bondlens/BondLensPage'

// AltSignal and PrivateAI Ops are designed stretch work (see
// docs/plans/design.md Section 0, "Scope revision - 2026-08-28") - only
// BondLens is built for the first release, so it is the only real route.
// Exported separately from the browser router instance so tests can build a
// createMemoryRouter from the same route definitions.
export const routes: RouteObject[] = [
  { path: '/', element: <Navigate to="/bondlens" replace /> },
  { path: '/bondlens', element: <BondLensPage /> },
]
