import { Link } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { useAuth } from '../context/AuthContext'
import { dashboardPathForRole } from '../components/layout/dashboardPath'

export default function Unauthorized() {
  const { user, role } = useAuth()
  return (
    <AppShell>
      <div className="flex min-h-[50vh] flex-col items-center justify-center text-center">
        <h1 className="text-2xl font-bold text-slate-900">Not authorized</h1>
        <p className="mt-2 max-w-sm text-sm text-slate-500">
          Your account doesn&rsquo;t have access to this page.
        </p>
        <Link to={user ? dashboardPathForRole(role) : '/'} className="mt-6">
          <Button>{user ? 'Go to my dashboard' : 'Go home'}</Button>
        </Link>
      </div>
    </AppShell>
  )
}
