import type { Role } from '../../types'

/** Where a logged-in user's "home" dashboard lives, by role. */
export function dashboardPathForRole(role: Role | null): string {
  switch (role) {
    case 'tourist':
      return '/tourist'
    case 'citizen':
      return '/citizen'
    case 'police':
      return '/police'
    case 'admin':
      return '/admin'
    case 'emergency_team':
      return '/emergency'
    default:
      return '/'
  }
}
