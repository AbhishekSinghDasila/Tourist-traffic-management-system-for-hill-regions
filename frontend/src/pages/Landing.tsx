import { Link } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { Card, CardBody } from '../components/ui/Card'
import { useAuth } from '../context/AuthContext'
import { dashboardPathForRole } from '../components/layout/dashboardPath'

const features = [
  {
    title: 'Live crowd & traffic density',
    body: 'See real-time vehicle density across hill districts, color-coded by risk, before you set out.',
  },
  {
    title: 'Crowd prediction',
    body: 'Plan ahead — check the forecast for any district on any future date.',
  },
  {
    title: 'Emergency alerts',
    body: 'Get notified of landslides, floods, and accidents near your location as they happen.',
  },
  {
    title: 'File a complaint in seconds',
    body: 'Report reckless driving, littering, or overcharging with a photo — routed straight to the nearest police station.',
  },
]

export default function Landing() {
  const { user, role } = useAuth()

  return (
    <AppShell>
      <section className="grid gap-8 py-8 sm:py-14 md:grid-cols-2 md:items-center">
        <div>
          <h1 className="text-3xl font-bold leading-tight tracking-tight text-slate-900 sm:text-4xl">
            Smart Traffic &amp; Tourism Management for the Himalayan hill regions
          </h1>
          <p className="mt-4 text-base text-slate-600">
            DevBhumi keeps tourists informed, citizens heard, and first responders coordinated across
            Uttarakhand and Himachal Pradesh&rsquo;s hill districts.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            {user ? (
              <Link to={dashboardPathForRole(role)}>
                <Button size="lg">Go to my dashboard</Button>
              </Link>
            ) : (
              <>
                <Link to="/register">
                  <Button size="lg">Get started</Button>
                </Link>
                <Link to="/login">
                  <Button size="lg" variant="outline">
                    Log in
                  </Button>
                </Link>
              </>
            )}
            <Link to="/complaints/new">
              <Button size="lg" variant="ghost">
                File a complaint
              </Button>
            </Link>
          </div>
        </div>
        <div className="overflow-hidden rounded-2xl border border-brand-100 bg-gradient-to-br from-brand-600 to-brand-800 p-8 text-white shadow-lg">
          <p className="text-sm font-medium uppercase tracking-wide text-brand-200">Built for hill terrain</p>
          <p className="mt-3 text-lg font-semibold">
            Weak connectivity, narrow roads, high season crowds — designed with all of it in mind.
          </p>
        </div>
      </section>

      <section className="grid gap-4 py-8 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((f) => (
          <Card key={f.title}>
            <CardBody>
              <h3 className="font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{f.body}</p>
            </CardBody>
          </Card>
        ))}
      </section>
    </AppShell>
  )
}
