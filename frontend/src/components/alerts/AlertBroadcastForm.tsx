import { useState, type FormEvent } from 'react'
import { Button } from '../ui/Button'
import { ErrorBanner, SuccessBanner } from '../ui/ErrorBanner'
import { Input, Select, Textarea } from '../ui/Input'
import { triggerAlert } from '../../api/alerts'
import { apiErrorMessage } from '../../api/client'
import { ALERT_TYPES, type AlertPublic, type AlertType } from '../../types'
import { useAuth } from '../../context/AuthContext'

export function AlertBroadcastForm({ onBroadcast }: { onBroadcast?: (alert: AlertPublic) => void }) {
  const { user } = useAuth()
  const [alertType, setAlertType] = useState<AlertType>('AMBULANCE')
  const [description, setDescription] = useState('')
  const [lat, setLat] = useState('')
  const [lng, setLng] = useState('')
  const [district, setDistrict] = useState(user?.district ?? '')
  const [radiusKm, setRadiusKm] = useState('2')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<AlertPublic | null>(null)

  function useMyLocation() {
    if (!navigator.geolocation) return
    navigator.geolocation.getCurrentPosition((pos) => {
      setLat(pos.coords.latitude.toFixed(6))
      setLng(pos.coords.longitude.toFixed(6))
    })
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    const latNum = Number(lat)
    const lngNum = Number(lng)
    if (Number.isNaN(latNum) || Number.isNaN(lngNum)) {
      setError('Please provide a valid latitude and longitude for the incident.')
      return
    }
    setSubmitting(true)
    try {
      const alert = await triggerAlert({
        alert_type: alertType,
        description: description || undefined,
        lat: latNum,
        lng: lngNum,
        district: district || undefined,
        radius_km: Number(radiusKm) || undefined,
      })
      setSuccess(alert)
      setDescription('')
      onBroadcast?.(alert)
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not broadcast the alert.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      {error && <ErrorBanner message={error} />}
      {success && <SuccessBanner message={`Alert broadcast — ${success.recipients_notified} people notified.`} />}

      <Select id="alert_type" label="Alert type" value={alertType} onChange={(e) => setAlertType(e.target.value as AlertType)}>
        {ALERT_TYPES.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </Select>

      <Textarea
        id="alert_description"
        label="Description (optional)"
        rows={2}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />

      <div className="grid grid-cols-2 gap-3">
        <Input id="alert_lat" label="Latitude" inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} required />
        <Input id="alert_lng" label="Longitude" inputMode="decimal" value={lng} onChange={(e) => setLng(e.target.value)} required />
      </div>
      <Button type="button" variant="outline" size="sm" onClick={useMyLocation}>
        Use my current location
      </Button>

      <Input
        id="alert_district"
        label="District (optional — defaults to your assigned district)"
        value={district}
        onChange={(e) => setDistrict(e.target.value)}
      />

      <Input
        id="alert_radius"
        label="Radius (km)"
        type="number"
        min={0.5}
        max={10}
        step={0.5}
        value={radiusKm}
        onChange={(e) => setRadiusKm(e.target.value)}
        hint="0.5–10 km"
      />

      <Button type="submit" variant="danger" loading={submitting} className="mt-2 w-full">
        Broadcast emergency alert
      </Button>
    </form>
  )
}
