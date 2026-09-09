import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppShell, PageHeader } from '../../components/layout/AppShell'
import { Card, CardBody, CardHeader } from '../../components/ui/Card'
import { Badge, statusTone } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ErrorBanner } from '../../components/ui/ErrorBanner'
import { PageSpinner } from '../../components/ui/Spinner'
import { fetchMyComplaints } from '../../api/complaints'
import { apiErrorMessage } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import type { ComplaintPublic } from '../../types'

export default function CitizenDashboard() {
  const { user } = useAuth()
  const [complaints, setComplaints] = useState<ComplaintPublic[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    setError(null)
    fetchMyComplaints()
      .then(setComplaints)
      .catch((err) => setError(apiErrorMessage(err, 'Could not load your complaints.')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  return (
    <AppShell>
      <PageHeader title={`Welcome${user ? `, ${user.name}` : ''}`} subtitle="Your submitted complaints" />

      <div className="mb-6 flex justify-end">
        <Link to="/complaints/new">
          <Button>File a new complaint</Button>
        </Link>
      </div>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">My complaints</h2>
          <button onClick={load} className="text-xs font-medium text-brand-700 hover:underline">
            Refresh
          </button>
        </CardHeader>
        <CardBody>
          {loading && <PageSpinner />}
          {error && <ErrorBanner message={error} />}
          {!loading && !error && complaints && complaints.length === 0 && (
            <p className="text-sm text-slate-500">You haven&rsquo;t filed any complaints yet.</p>
          )}
          {!loading && !error && complaints && complaints.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-2 pr-4 font-medium">Category</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                    <th className="py-2 pr-4 font-medium">Filed on</th>
                  </tr>
                </thead>
                <tbody>
                  {complaints.map((c) => (
                    <tr key={c.id} className="border-b border-slate-100 last:border-0">
                      <td className="py-3 pr-4">{c.category.replaceAll('_', ' ')}</td>
                      <td className="py-3 pr-4">
                        <Badge tone={statusTone(c.status)}>{c.status.replaceAll('_', ' ')}</Badge>
                      </td>
                      <td className="py-3 pr-4 text-slate-500">{new Date(c.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </AppShell>
  )
}
