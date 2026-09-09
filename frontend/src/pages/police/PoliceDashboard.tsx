import { useEffect, useState } from 'react'
import { AppShell, PageHeader } from '../../components/layout/AppShell'
import { Card, CardBody, CardHeader } from '../../components/ui/Card'
import { Badge, statusTone } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ErrorBanner } from '../../components/ui/ErrorBanner'
import { PageSpinner } from '../../components/ui/Spinner'
import { ActiveAlertsList } from '../../components/alerts/ActiveAlertsList'
import { AlertBroadcastForm } from '../../components/alerts/AlertBroadcastForm'
import { fetchStationComplaints, updateComplaintStatus } from '../../api/complaints'
import { fetchActiveAlerts, fetchAlertHistory } from '../../api/alerts'
import { apiErrorMessage } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { COMPLAINT_STATUSES, type AlertPublic, type ComplaintPoliceView, type ComplaintStatus } from '../../types'

function ComplaintRow({ complaint, onUpdated }: { complaint: ComplaintPoliceView; onUpdated: (c: ComplaintPoliceView) => void }) {
  const [status, setStatus] = useState<ComplaintStatus>(complaint.status)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function saveStatus() {
    if (status === complaint.status) return
    setUpdating(true)
    setError(null)
    try {
      await updateComplaintStatus(complaint.id, { status })
      onUpdated({ ...complaint, status })
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not update status.'))
      setStatus(complaint.status)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <tr className="border-b border-slate-100 align-top last:border-0">
      <td className="py-3 pr-4">{complaint.category.replaceAll('_', ' ')}</td>
      <td className="py-3 pr-4">{complaint.plate_number ?? <span className="text-slate-400">—</span>}</td>
      <td className="max-w-[16rem] py-3 pr-4 text-slate-600">{complaint.description ?? <span className="text-slate-400">—</span>}</td>
      <td className="py-3 pr-4 text-slate-500">{new Date(complaint.created_at).toLocaleDateString()}</td>
      <td className="py-3 pr-4">
        <div className="flex items-center gap-2">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as ComplaintStatus)}
            className="rounded-md border border-slate-300 px-2 py-1 text-xs"
          >
            {COMPLAINT_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replaceAll('_', ' ')}
              </option>
            ))}
          </select>
          <Button size="sm" variant="outline" onClick={saveStatus} loading={updating} disabled={status === complaint.status}>
            Save
          </Button>
        </div>
        {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      </td>
      <td className="py-3 pr-4">
        <Badge tone={statusTone(complaint.status)}>{complaint.status.replaceAll('_', ' ')}</Badge>
      </td>
    </tr>
  )
}

export default function PoliceDashboard() {
  const { user } = useAuth()
  const [complaints, setComplaints] = useState<ComplaintPoliceView[] | null>(null)
  const [complaintsError, setComplaintsError] = useState<string | null>(null)
  const [loadingComplaints, setLoadingComplaints] = useState(true)

  const [alerts, setAlerts] = useState<AlertPublic[]>([])
  const [history, setHistory] = useState<AlertPublic[]>([])
  const [alertsError, setAlertsError] = useState<string | null>(null)
  const [loadingAlerts, setLoadingAlerts] = useState(true)
  const [showBroadcast, setShowBroadcast] = useState(false)

  function loadComplaints() {
    setLoadingComplaints(true)
    setComplaintsError(null)
    fetchStationComplaints()
      .then(setComplaints)
      .catch((err) => setComplaintsError(apiErrorMessage(err, 'Could not load station complaints.')))
      .finally(() => setLoadingComplaints(false))
  }

  function loadAlerts() {
    setLoadingAlerts(true)
    setAlertsError(null)
    Promise.all([fetchActiveAlerts(user?.district ?? undefined), fetchAlertHistory()])
      .then(([active, hist]) => {
        setAlerts(active)
        setHistory(hist)
      })
      .catch((err) => setAlertsError(apiErrorMessage(err, 'Could not load alerts.')))
      .finally(() => setLoadingAlerts(false))
  }

  useEffect(() => {
    loadComplaints()
    loadAlerts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <AppShell>
      <PageHeader title="Police dashboard" subtitle={user?.district ? `Station district: ${user.district}` : undefined} />

      <Card className="mb-6">
        <CardHeader className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Complaints routed to your station</h2>
          <button onClick={loadComplaints} className="text-xs font-medium text-brand-700 hover:underline">
            Refresh
          </button>
        </CardHeader>
        <CardBody>
          {loadingComplaints && <PageSpinner />}
          {complaintsError && <ErrorBanner message={complaintsError} />}
          {!loadingComplaints && !complaintsError && complaints && complaints.length === 0 && (
            <p className="text-sm text-slate-500">No complaints assigned to your station right now.</p>
          )}
          {!loadingComplaints && !complaintsError && complaints && complaints.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-2 pr-4 font-medium">Category</th>
                    <th className="py-2 pr-4 font-medium">Plate</th>
                    <th className="py-2 pr-4 font-medium">Description</th>
                    <th className="py-2 pr-4 font-medium">Filed</th>
                    <th className="py-2 pr-4 font-medium">Update status</th>
                    <th className="py-2 pr-4 font-medium">Current</th>
                  </tr>
                </thead>
                <tbody>
                  {complaints.map((c) => (
                    <ComplaintRow
                      key={c.id}
                      complaint={c}
                      onUpdated={(updated) => setComplaints((prev) => prev?.map((p) => (p.id === updated.id ? updated : p)) ?? null)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Emergency alerts</h2>
            <Button size="sm" variant="secondary" onClick={() => setShowBroadcast((v) => !v)}>
              {showBroadcast ? 'Cancel' : 'Broadcast alert'}
            </Button>
          </CardHeader>
          <CardBody>
            {showBroadcast && (
              <div className="mb-4 border-b border-slate-100 pb-4">
                <AlertBroadcastForm
                  onBroadcast={(a) => {
                    setAlerts((prev) => [a, ...prev])
                    setHistory((prev) => [a, ...prev])
                    setShowBroadcast(false)
                  }}
                />
              </div>
            )}
            {loadingAlerts && <PageSpinner />}
            {alertsError && <ErrorBanner message={alertsError} />}
            {!loadingAlerts && !alertsError && <ActiveAlertsList alerts={alerts} />}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="font-semibold text-slate-900">Recent alert history</h2>
          </CardHeader>
          <CardBody>
            {!loadingAlerts && !alertsError && (
              <ActiveAlertsList alerts={history} emptyMessage="No alert history yet." />
            )}
          </CardBody>
        </Card>
      </div>
    </AppShell>
  )
}
