import { Badge, statusTone } from '../ui/Badge'
import { Card, CardBody } from '../ui/Card'
import type { AlertPublic } from '../../types'

const alertTypeIcon: Record<string, string> = {
  AMBULANCE: '🚑',
  ACCIDENT: '🚧',
  LANDSLIDE: '⛰️',
  FLOOD: '🌊',
  FIRE: '🔥',
  OTHER: '⚠️',
}

export function ActiveAlertsList({
  alerts,
  emptyMessage = 'No active alerts right now.',
  onCancel,
}: {
  alerts: AlertPublic[]
  emptyMessage?: string
  onCancel?: (alert: AlertPublic) => void
}) {
  if (alerts.length === 0) {
    return <p className="text-sm text-slate-500">{emptyMessage}</p>
  }

  return (
    <div className="flex flex-col gap-3">
      {alerts.map((alert) => (
        <Card key={alert.id}>
          <CardBody className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span aria-hidden="true">{alertTypeIcon[alert.alert_type] ?? '⚠️'}</span>
                <span className="font-semibold text-slate-900">{alert.alert_type.replaceAll('_', ' ')}</span>
                <Badge tone={statusTone(alert.status)}>{alert.status}</Badge>
              </div>
              {alert.description && <p className="mt-1 text-sm text-slate-600">{alert.description}</p>}
              <p className="mt-1 text-xs text-slate-400">
                {alert.district ? `${alert.district} · ` : ''}
                {alert.radius_km} km radius · {alert.recipients_notified} notified ·{' '}
                {new Date(alert.created_at).toLocaleString()}
              </p>
            </div>
            {onCancel && alert.status === 'ACTIVE' && (
              <button
                onClick={() => onCancel(alert)}
                className="whitespace-nowrap text-xs font-medium text-red-600 hover:underline"
              >
                Cancel
              </button>
            )}
          </CardBody>
        </Card>
      ))}
    </div>
  )
}
