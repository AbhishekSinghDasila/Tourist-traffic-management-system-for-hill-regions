import { useEffect, useState } from 'react'
import { AppShell, PageHeader } from '../../components/layout/AppShell'
import { Card, CardBody, CardHeader } from '../../components/ui/Card'
import { ErrorBanner } from '../../components/ui/ErrorBanner'
import { PageSpinner } from '../../components/ui/Spinner'
import { ActiveAlertsList } from '../../components/alerts/ActiveAlertsList'
import { AlertBroadcastForm } from '../../components/alerts/AlertBroadcastForm'
import { fetchActiveAlerts } from '../../api/alerts'
import { apiErrorMessage } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import type { AlertPublic } from '../../types'

export default function EmergencyDashboard() {
  const { user } = useAuth()
  const [alerts, setAlerts] = useState<AlertPublic[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    setError(null)
    fetchActiveAlerts(user?.district ?? undefined)
      .then(setAlerts)
      .catch((err) => setError(apiErrorMessage(err, 'Could not load alerts.')))
      .finally(() => setLoading(false))
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [])

  return (
    <AppShell>
      <PageHeader
        title="Emergency response"
        subtitle={user?.district ? `Assigned district: ${user.district}` : 'Broadcast and track active alerts'}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-slate-900">Broadcast an alert</h2>
          </CardHeader>
          <CardBody>
            <AlertBroadcastForm onBroadcast={(a) => setAlerts((prev) => [a, ...prev])} />
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Active alerts</h2>
            <button onClick={load} className="text-xs font-medium text-brand-700 hover:underline">
              Refresh
            </button>
          </CardHeader>
          <CardBody>
            {loading && <PageSpinner />}
            {error && <ErrorBanner message={error} />}
            {!loading && !error && <ActiveAlertsList alerts={alerts} />}
          </CardBody>
        </Card>
      </div>
    </AppShell>
  )
}
