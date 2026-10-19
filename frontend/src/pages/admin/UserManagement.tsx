import { useEffect, useState, type FormEvent } from 'react'
import { apiClient, apiErrorMessage } from '../../api/client'
import type { UserPublic, Role } from '../../types'
import { Card, CardBody, CardHeader } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { ErrorBanner } from '../../components/ui/ErrorBanner'

export function UserManagement() {
  const [users, setUsers] = useState<UserPublic[]>([])
  const [offset, setOffset] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [revision, setRevision] = useState(0)
  const [role, setRole] = useState<Role>('police')
  useEffect(() => {
    let active = true
    apiClient.get<UserPublic[]>('/api/v1/auth/users', { params: { offset, limit: 20 } })
      .then(({ data }) => { if (active) setUsers(data) })
      .catch(err => { if (active) setError(apiErrorMessage(err)) })
    return () => { active = false }
  }, [offset, revision])

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const data = new FormData(form)
    setBusy(true)
    setError(null)
    try {
      await apiClient.post('/api/v1/auth/users', {
        name: data.get('name'), phone: data.get('phone'), password: data.get('password'),
        role, district: data.get('district') || null, station_id: data.get('station_id') || null,
      })
      form.reset()
      setRevision(v => v + 1)
    } catch (err) { setError(apiErrorMessage(err)) }
    finally { setBusy(false) }
  }

  return <Card>
    <CardHeader><h2 className="font-semibold">User accounts</h2></CardHeader>
    <CardBody>
      {error && <ErrorBanner message={error} />}
      <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
        <Input label="Full name" id="managed-name" name="name" required maxLength={120} />
        <Input label="Phone" id="managed-phone" name="phone" required pattern="\+?[0-9]{10,15}" />
        <Input label="Initial password" id="managed-password" name="password" type="password" required minLength={8} autoComplete="new-password" />
        <label className="text-sm">Role
          <select className="mt-1 block w-full rounded border p-2" value={role} onChange={e => setRole(e.target.value as Role)}>
            {(['police', 'emergency_team', 'admin', 'citizen', 'tourist'] as Role[]).map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <Input label="District (required for police)" id="managed-district" name="district" required={role === 'police'} maxLength={80} />
        <Input label="Station ID (optional)" id="managed-station_id" name="station_id" maxLength={80} />
        <Button type="submit" loading={busy}>Create account</Button>
      </form>
      <p className="mt-2 text-xs text-slate-500">Passwords need an uppercase letter and a digit, and must be 8 characters or longer.</p>
      <div className="mt-5 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead><tr><th>Name</th><th>Phone</th><th>Role</th><th>District</th></tr></thead>
          <tbody>{users.map(u => <tr key={u.id} className="border-t"><td className="py-2">{u.name}</td><td>{u.phone}</td><td>{u.role}</td><td>{u.district || '—'}</td></tr>)}</tbody>
        </table>
      </div>
      <div className="mt-3 flex gap-3">
        <Button variant="outline" disabled={offset === 0} onClick={() => setOffset(v => Math.max(0, v - 20))}>Previous</Button>
        <Button variant="outline" disabled={users.length < 20} onClick={() => setOffset(v => v + 20)}>Next</Button>
      </div>
    </CardBody>
  </Card>
}
