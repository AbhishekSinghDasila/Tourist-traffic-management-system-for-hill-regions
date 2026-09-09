import { useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { AppShell, PageHeader } from '../components/layout/AppShell'
import { Card, CardBody } from '../components/ui/Card'
import { Input, Select, Textarea } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { ErrorBanner, InfoBanner, SuccessBanner } from '../components/ui/ErrorBanner'
import { useAuth } from '../context/AuthContext'
import { submitComplaint } from '../api/complaints'
import { apiErrorMessage } from '../api/client'
import { COMPLAINT_CATEGORIES, KNOWN_DISTRICTS, type ComplaintCategory, type ComplaintPublic } from '../types'

export default function ComplaintFormPage() {
  const { user, initializing } = useAuth()
  const [category, setCategory] = useState<ComplaintCategory>('OTHER')
  const [description, setDescription] = useState('')
  const [district, setDistrict] = useState('')
  const [lat, setLat] = useState('')
  const [lng, setLng] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const [locating, setLocating] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ComplaintPublic | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  function useMyLocation() {
    if (!navigator.geolocation) {
      setError('Geolocation is not available in this browser.')
      return
    }
    setLocating(true)
    setError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6))
        setLng(pos.coords.longitude.toFixed(6))
        setLocating(false)
      },
      () => {
        setError('Could not get your location. You can enter latitude/longitude manually.')
        setLocating(false)
      },
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (!image) {
      setError('Please attach a photo of the incident/vehicle.')
      return
    }
    const latNum = Number(lat)
    const lngNum = Number(lng)
    if (Number.isNaN(latNum) || Number.isNaN(lngNum)) {
      setError('Please provide a valid latitude and longitude.')
      return
    }

    setSubmitting(true)
    try {
      const complaint = await submitComplaint({
        image,
        category,
        description: description || undefined,
        lat: latNum,
        lng: lngNum,
        district: district || undefined,
      })
      setResult(complaint)
      setDescription('')
      setImage(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not submit the complaint. Please try again.'))
    } finally {
      setSubmitting(false)
    }
  }

  if (initializing) {
    return (
      <AppShell>
        <PageHeader title="File a complaint" />
      </AppShell>
    )
  }

  // The backend requires an authenticated citizen/police/admin/emergency_team
  // account to submit a complaint (require_role in complaint-service — see
  // src/api/complaints.ts for the full note). We surface that plainly rather
  // than showing a form that will just fail with a 401.
  if (!user) {
    return (
      <AppShell>
        <PageHeader title="File a complaint" subtitle="Report an incident to the nearest police station" />
        <InfoBanner message="You need to log in with a citizen account to submit a complaint." />
        <div className="mt-4 flex gap-3">
          <Link to="/login">
            <Button>Log in</Button>
          </Link>
          <Link to="/register">
            <Button variant="outline">Create an account</Button>
          </Link>
        </div>
      </AppShell>
    )
  }

  if (user.role === 'tourist') {
    return (
      <AppShell>
        <PageHeader title="File a complaint" />
        <InfoBanner message="Complaint filing is currently available to citizen accounts (and police/admin/emergency staff), not tourist accounts. Register a citizen account if you're a resident, or reach out to local police directly." />
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-lg">
        <PageHeader title="File a complaint" subtitle="Your identity is never shared with the police officer reviewing this report" />
        <Card>
          <CardBody>
            {result ? (
              <div className="flex flex-col gap-4">
                <SuccessBanner message={`Complaint submitted (status: ${result.status}). Thank you for the report.`} />
                <Button variant="outline" onClick={() => setResult(null)}>
                  File another complaint
                </Button>
              </div>
            ) : (
              <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
                {error && <ErrorBanner message={error} />}

                <div className="flex flex-col gap-1">
                  <label htmlFor="image" className="text-sm font-medium text-slate-700">
                    Photo of the incident/vehicle
                  </label>
                  <input
                    id="image"
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={(e) => setImage(e.target.files?.[0] ?? null)}
                    className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100"
                    required
                  />
                </div>

                <Select
                  id="category"
                  label="Category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value as ComplaintCategory)}
                >
                  {COMPLAINT_CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c.replaceAll('_', ' ')}
                    </option>
                  ))}
                </Select>

                <Textarea
                  id="description"
                  label="Description (optional)"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />

                <div className="grid grid-cols-2 gap-3">
                  <Input
                    id="lat"
                    label="Latitude"
                    inputMode="decimal"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                    required
                  />
                  <Input
                    id="lng"
                    label="Longitude"
                    inputMode="decimal"
                    value={lng}
                    onChange={(e) => setLng(e.target.value)}
                    required
                  />
                </div>
                <Button type="button" variant="outline" size="sm" onClick={useMyLocation} loading={locating}>
                  Use my current location
                </Button>

                <Select id="district" label="District (optional)" value={district} onChange={(e) => setDistrict(e.target.value)}>
                  <option value="">Select a district</option>
                  {KNOWN_DISTRICTS.map((d) => (
                    <option key={d} value={d}>
                      {d[0].toUpperCase() + d.slice(1)}
                    </option>
                  ))}
                </Select>

                <Button type="submit" loading={submitting} className="mt-2 w-full">
                  Submit complaint
                </Button>
              </form>
            )}
          </CardBody>
        </Card>
      </div>
    </AppShell>
  )
}
