import { Link } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'

export default function NotFound() {
  return (
    <AppShell>
      <div className="flex min-h-[50vh] flex-col items-center justify-center text-center">
        <h1 className="text-2xl font-bold text-slate-900">Page not found</h1>
        <p className="mt-2 max-w-sm text-sm text-slate-500">The page you&rsquo;re looking for doesn&rsquo;t exist.</p>
        <Link to="/" className="mt-6">
          <Button>Go home</Button>
        </Link>
      </div>
    </AppShell>
  )
}
