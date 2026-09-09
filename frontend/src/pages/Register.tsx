import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AppShell, PageHeader } from '../components/layout/AppShell'
import { Card, CardBody } from '../components/ui/Card'
import { Input, Select } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { ErrorBanner, SuccessBanner } from '../components/ui/ErrorBanner'
import { register } from '../api/auth'
import { apiErrorMessage } from '../api/client'
import { KNOWN_DISTRICTS } from '../types'

export default function Register() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'tourist' | 'citizen'>('tourist')
  const [district, setDistrict] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await register({
        name,
        phone,
        email: email || undefined,
        password,
        role,
        district: district || undefined,
      })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 1200)
    } catch (err) {
      setError(apiErrorMessage(err, 'Registration failed. Please check your details.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-sm py-8">
        <PageHeader title="Create an account" subtitle="Tourist and citizen accounts can self-register" />
        <Card>
          <CardBody>
            <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
              {error && <ErrorBanner message={error} />}
              {success && <SuccessBanner message="Account created! Redirecting to login…" />}

              <Input id="name" label="Full name" value={name} onChange={(e) => setName(e.target.value)} required />
              <Input
                id="phone"
                label="Phone number"
                type="tel"
                placeholder="+919876543210"
                hint="10-15 digits, optional leading +"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
              />
              <Input
                id="email"
                label="Email (optional)"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <Input
                id="password"
                label="Password"
                type="password"
                hint="At least 8 characters, one uppercase letter, one digit"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <Select id="role" label="Account type" value={role} onChange={(e) => setRole(e.target.value as 'tourist' | 'citizen')}>
                <option value="tourist">Tourist</option>
                <option value="citizen">Citizen (resident)</option>
              </Select>
              <Select
                id="district"
                label="District (optional)"
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
              >
                <option value="">Select a district</option>
                {KNOWN_DISTRICTS.map((d) => (
                  <option key={d} value={d} className="capitalize">
                    {d[0].toUpperCase() + d.slice(1)}
                  </option>
                ))}
              </Select>

              <Button type="submit" loading={submitting} className="mt-2 w-full">
                Create account
              </Button>
            </form>
          </CardBody>
        </Card>
        <p className="mt-4 text-center text-sm text-slate-500">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-brand-700 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </AppShell>
  )
}
