import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AppShell, PageHeader } from '../components/layout/AppShell'
import { Card, CardBody } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { useAuth } from '../context/AuthContext'
import { apiErrorMessage } from '../api/client'
import { dashboardPathForRole } from '../components/layout/dashboardPath'

interface LocationState {
  from?: { pathname: string }
}

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const user = await login(phone, password)
      const state = location.state as LocationState | null
      const redirectTo = state?.from?.pathname || dashboardPathForRole(user.role)
      navigate(redirectTo, { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err, 'Login failed. Check your phone number and password.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-sm py-8">
        <PageHeader title="Log in" subtitle="Access your DevBhumi dashboard" />
        <Card>
          <CardBody>
            <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
              {error && <ErrorBanner message={error} />}
              <Input
                id="phone"
                label="Phone number"
                type="tel"
                autoComplete="tel"
                placeholder="+919876543210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
              />
              <Input
                id="password"
                label="Password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <Button type="submit" loading={submitting} className="mt-2 w-full">
                Log in
              </Button>
            </form>
          </CardBody>
        </Card>
        <p className="mt-4 text-center text-sm text-slate-500">
          New here?{' '}
          <Link to="/register" className="font-medium text-brand-700 hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </AppShell>
  )
}
