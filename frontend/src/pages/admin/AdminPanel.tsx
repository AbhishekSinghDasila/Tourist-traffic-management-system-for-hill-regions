import { UserManagement } from './UserManagement'
import { useEffect, useState, type FormEvent } from 'react'
import { AppShell, PageHeader } from '../../components/layout/AppShell'
import { Card, CardBody, CardHeader } from '../../components/ui/Card'
import { Badge, statusTone } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { ErrorBanner } from '../../components/ui/ErrorBanner'
import { PageSpinner } from '../../components/ui/Spinner'
import { ActiveAlertsList } from '../../components/alerts/ActiveAlertsList'
import { AlertBroadcastForm } from '../../components/alerts/AlertBroadcastForm'
import { cancelAlert, fetchAlertHistory } from '../../api/alerts'
import { fetchComplaintAdminView, fetchComplaintImageUrls, type ImageUrlEntry } from '../../api/complaints'
import { apiErrorMessage } from '../../api/client'
import type { AlertPublic, ComplaintAdminView } from '../../types'

function ComplaintLookup() {
  const [complaintId, setComplaintId] = useState('')
  const [complaint, setComplaint] = useState<ComplaintAdminView | null>(null)
  const [images, setImages] = useState<ImageUrlEntry[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingImages, setLoadingImages] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleLookup(e: FormEvent) {
    e.preventDefault()
    if (!complaintId.trim()) return
    setLoading(true)
    setError(null)
    setComplaint(null)
    setImages(null)
    try {
      const res = await fetchComplaintAdminView(complaintId.trim())
      setComplaint(res)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not find that complaint.'))
    } finally {
      setLoading(false)
    }
  }

  async function loadImages() {
    if (!complaint) return
    setLoadingImages(true)
    try {
      const res = await fetchComplaintImageUrls(complaint.id)
      setImages(res.images)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not generate an image URL.'))
    } finally {
      setLoadingImages(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <h2 className="font-semibold text-slate-900">Look up a complaint</h2>
      </CardHeader>
      <CardBody>

        <form className="flex items-end gap-3" onSubmit={handleLookup}>
          <div className="flex-1">
            <Input
              id="complaint-id"
              label="Complaint ID"
              placeholder="UUID"
              value={complaintId}
              onChange={(e) => setComplaintId(e.target.value)}
            />
          </div>
          <Button type="submit" loading={loading}>
            Look up
          </Button>
        </form>

        {error && <ErrorBanner message={error} className="mt-4" />}

        {complaint && (
          <div className="mt-5 rounded-lg border border-slate-200 p-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-slate-900">{complaint.category.replaceAll('_', ' ')}</h3>
              <Badge tone={statusTone(complaint.status)}>{complaint.status.replaceAll('_', ' ')}</Badge>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-slate-500">Reporting user ID</dt>
              <dd className="font-mono text-xs">{complaint.user_id}</dd>
              <dt className="text-slate-500">Plate</dt>
              <dd>{complaint.plate_number ?? '—'}</dd>
              <dt className="text-slate-500">Vehicle state</dt>
              <dd>{complaint.vehicle_state ?? '—'}</dd>
              <dt className="text-slate-500">Description</dt>
              <dd>{complaint.description ?? '—'}</dd>
              <dt className="text-slate-500">Location</dt>
              <dd>
                {complaint.lat.toFixed(4)}, {complaint.lng.toFixed(4)}
              </dd>
              <dt className="text-slate-500">District</dt>
              <dd>{complaint.district ?? '—'}</dd>
              <dt className="text-slate-500">Flag reason</dt>
              <dd>{complaint.flag_reason ?? '—'}</dd>
              <dt className="text-slate-500">Filed</dt>
              <dd>{new Date(complaint.created_at).toLocaleString()}</dd>
              <dt className="text-slate-500">Updated</dt>
              <dd>{new Date(complaint.updated_at).toLocaleString()}</dd>
            </dl>

            <div className="mt-4 border-t border-slate-100 pt-4">
              <Button size="sm" variant="outline" onClick={loadImages} loading={loadingImages}>
                Generate image URL(s)
              </Button>
              {images && (
                <ul className="mt-2 flex flex-col gap-1 text-xs">
                  {images.length === 0 && <li className="text-slate-500">No media attached.</li>}
                  {images.map((img) => (
                    <li key={img.media_id}>
                      {img.url ? (
                        <a href={img.url} target="_blank" rel="noreferrer" className="text-brand-700 hover:underline">
                          {img.media_id} (expires in {img.expires_in}s)
                        </a>
                      ) : (
                        <span className="text-red-600">
                          {img.media_id}: {img.error ?? 'unavailable'}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  )
}

function AlertAdministration() {
  const [history, setHistory] = useState<AlertPublic[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [showBroadcast, setShowBroadcast] = useState(false)

  function load() {
    setLoading(true)
    setError(null)
    fetchAlertHistory()
      .then(setHistory)
      .catch((err) => setError(apiErrorMessage(err, 'Could not load alert history.')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  async function handleCancel(alert: AlertPublic) {
    const reason = window.prompt('Reason for cancelling this alert (optional):')
    if (reason === null) return
    try {
      const updated = await cancelAlert(alert.id, reason)
      setHistory((prev) => prev?.map((a) => (a.id === updated.id ? updated : a)) ?? null)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not cancel the alert.'))
    }
  }

  const active = history?.filter((a) => a.status === 'ACTIVE') ?? []

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-900">Alert history &amp; administration</h2>
        <div className="flex items-center gap-3">
          <button onClick={load} className="text-xs font-medium text-brand-700 hover:underline">
            Refresh
          </button>
          <Button size="sm" variant="secondary" onClick={() => setShowBroadcast((v) => !v)}>
            {showBroadcast ? 'Cancel' : 'Broadcast alert'}
          </Button>
        </div>
      </CardHeader>
      <CardBody>
        {showBroadcast && (
          <div className="mb-4 border-b border-slate-100 pb-4">
            <AlertBroadcastForm
              onBroadcast={(a) => {
                setHistory((prev) => [a, ...(prev ?? [])])
                setShowBroadcast(false)
              }}
            />
          </div>
        )}
        {loading && <PageSpinner />}
        {error && <ErrorBanner message={error} />}
        {!loading && !error && history && (
          <>
            {active.length > 0 && (
              <div className="mb-4">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
                  Active — cancel a false alarm
                </p>
                <ActiveAlertsList alerts={active} onCancel={handleCancel} />
              </div>
            )}
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Full history</p>
            <ActiveAlertsList alerts={history} emptyMessage="No alerts have been triggered yet." />
          </>
        )}
      </CardBody>
    </Card>
  )
}

export default function AdminPanel() {
  return (
    <AppShell>
      <PageHeader title="Admin panel" subtitle="Complaint oversight and emergency alert administration" />

      <div className="flex flex-col gap-6">
        <UserManagement />
        <ComplaintLookup />
        <AlertAdministration />
      </div>


    </AppShell>
  )
}
