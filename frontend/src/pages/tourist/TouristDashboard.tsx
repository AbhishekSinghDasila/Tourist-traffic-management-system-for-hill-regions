import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { AppShell, PageHeader } from '../../components/layout/AppShell'
import { Card, CardBody, CardHeader } from '../../components/ui/Card'
import { Badge, riskTone } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ErrorBanner } from '../../components/ui/ErrorBanner'
import { PageSpinner, Spinner } from '../../components/ui/Spinner'
import { Select } from '../../components/ui/Input'
import { DensityMap } from '../../components/map/DensityMap'
import { ActiveAlertsList } from '../../components/alerts/ActiveAlertsList'
import { fetchAllDensity } from '../../api/traffic'
import { predictDistrictToday } from '../../api/predict'
import { fetchActiveAlerts, updateMyLocation } from '../../api/alerts'
import { apiErrorMessage } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import { KNOWN_DISTRICTS, type AlertPublic, type DensityListResponse, type PredictionResponse } from '../../types'

export default function TouristDashboard() {
  const { user } = useAuth()
  const [density, setDensity] = useState<DensityListResponse | null>(null)
  const [densityError, setDensityError] = useState<string | null>(null)
  const [loadingDensity, setLoadingDensity] = useState(true)

  const [alerts, setAlerts] = useState<AlertPublic[]>([])
  const [alertsError, setAlertsError] = useState<string | null>(null)
  const [loadingAlerts, setLoadingAlerts] = useState(true)

  const [predictDistrict, setPredictDistrict] = useState(user?.district ?? KNOWN_DISTRICTS[0])
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const [predictError, setPredictError] = useState<string | null>(null)
  const [predicting, setPredicting] = useState(false)

  const [sharingLocation, setSharingLocation] = useState(false)
  const [locationShared, setLocationShared] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)

  function shareLocation() {
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not available in this browser.')
      return
    }
    setSharingLocation(true)
    setLocationError(null)
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          await updateMyLocation({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            district: user?.district ?? undefined,
          })
          setLocationShared(true)
        } catch (err) {
          setLocationError(apiErrorMessage(err, 'Could not share your location.'))
        } finally {
          setSharingLocation(false)
        }
      },
      () => {
        setLocationError('Could not get your location.')
        setSharingLocation(false)
      },
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  useEffect(() => {
    fetchAllDensity()
      .then(setDensity)
      .catch((err) => setDensityError(apiErrorMessage(err, 'Could not load traffic density.')))
      .finally(() => setLoadingDensity(false))

    fetchActiveAlerts(user?.district ?? undefined)
      .then(setAlerts)
      .catch((err) => setAlertsError(apiErrorMessage(err, 'Could not load alerts.')))
      .finally(() => setLoadingAlerts(false))
  }, [user?.district])

  async function handlePredict(e: FormEvent) {
    e.preventDefault()
    setPredictError(null)
    setPredicting(true)
    try {
      const res = await predictDistrictToday(predictDistrict)
      setPrediction(res)
    } catch (err) {
      setPredictError(apiErrorMessage(err, 'Could not fetch prediction for this district.'))
    } finally {
      setPredicting(false)
    }
  }

  return (
    <AppShell>
      <PageHeader title={`Welcome${user ? `, ${user.name}` : ''}`} subtitle="Live conditions across the hills" />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">Live tourist density map</h2>
              {density && <span className="text-xs text-slate-400">{density.total_active_vehicles} vehicles active</span>}
            </CardHeader>
            <CardBody>
              {loadingDensity && <PageSpinner />}
              {densityError && <ErrorBanner message={densityError} />}
              {density && <DensityMap districts={density.districts} />}
            </CardBody>
          </Card>

          <Card className="mt-6">
            <CardHeader>
              <h2 className="font-semibold text-slate-900">Crowd prediction</h2>
            </CardHeader>
            <CardBody>
              <form className="flex flex-wrap items-end gap-3" onSubmit={handlePredict}>
                <div className="min-w-[10rem] flex-1">
                  <Select
                    id="predict-district"
                    label="District"
                    value={predictDistrict}
                    onChange={(e) => setPredictDistrict(e.target.value)}
                  >
                    {KNOWN_DISTRICTS.map((d) => (
                      <option key={d} value={d}>
                        {d[0].toUpperCase() + d.slice(1)}
                      </option>
                    ))}
                  </Select>
                </div>
                <Button type="submit" loading={predicting}>
                  Check today&rsquo;s forecast
                </Button>
              </form>
              {predictError && <ErrorBanner message={predictError} className="mt-3" />}
              {prediction && (
                <div className="mt-4 flex items-center gap-4 rounded-lg bg-slate-50 p-4">
                  <Badge tone={riskTone(prediction.risk_level)} className="text-sm">
                    {prediction.risk_level}
                  </Badge>
                  <div className="text-sm text-slate-700">
                    <p className="font-medium capitalize">{prediction.district}</p>
                    <p className="text-slate-500">
                      ~{prediction.predicted_vehicles} vehicles predicted ({prediction.capacity_pct.toFixed(1)}% of
                      capacity) for {prediction.target_date}
                    </p>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>
        </div>

        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <h2 className="font-semibold text-slate-900">Active emergency alerts</h2>
            </CardHeader>
            <CardBody>
              {loadingAlerts && <Spinner />}
              {alertsError && <ErrorBanner message={alertsError} />}
              {!loadingAlerts && !alertsError && <ActiveAlertsList alerts={alerts} />}
              <div className="mt-4 border-t border-slate-100 pt-4">
                <Button size="sm" variant="outline" onClick={shareLocation} loading={sharingLocation}>
                  Share my location for nearby alerts
                </Button>
                {locationShared && <p className="mt-2 text-xs text-emerald-600">Location shared.</p>}
                {locationError && <p className="mt-2 text-xs text-red-600">{locationError}</p>}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="font-semibold text-slate-900">Need to report something?</h2>
            </CardHeader>
            <CardBody>
              <p className="text-sm text-slate-600">
                Reckless driving, littering, or overcharging — let us know and it&rsquo;ll be routed to the nearest
                police station.
              </p>
              <Link to="/complaints/new" className="mt-3 inline-block">
                <Button variant="outline">File a complaint</Button>
              </Link>
            </CardBody>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}
