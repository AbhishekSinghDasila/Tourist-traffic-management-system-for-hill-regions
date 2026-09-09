import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { PageSpinner } from '../ui/Spinner'
import type { Role } from '../../types'

/** Requires an authenticated user; optionally restricts to a set of roles. */
export function ProtectedRoute({ children, roles }: { children: ReactNode; roles?: Role[] }) {
  const { user, role, initializing } = useAuth()
  const location = useLocation()

  if (initializing) return <PageSpinner />

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (roles && role && !roles.includes(role)) {
    return <Navigate to="/unauthorized" replace />
  }

  return <>{children}</>
}
