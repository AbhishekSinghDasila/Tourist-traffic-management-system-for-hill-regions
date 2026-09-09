import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { Button } from '../ui/Button'
import { dashboardPathForRole } from './dashboardPath'

const roleLabels: Record<string, string> = {
  tourist: 'Tourist',
  citizen: 'Citizen',
  police: 'Police',
  admin: 'Admin',
  emergency_team: 'Emergency Team',
}

export function Navbar() {
  const { user, role, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)

  async function handleLogout() {
    setLoggingOut(true)
    try {
      await logout()
      navigate('/login')
    } finally {
      setLoggingOut(false)
    }
  }

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to={user ? dashboardPathForRole(role) : '/'} className="flex items-center gap-2 font-semibold text-brand-800">
          <img src="/mountain.svg" alt="" className="h-8 w-8 rounded" />
          <span className="text-lg tracking-tight">DevBhumi</span>
        </Link>

        <button
          className="rounded-md p-2 text-slate-600 hover:bg-slate-100 sm:hidden"
          aria-label="Toggle menu"
          onClick={() => setMenuOpen((v) => !v)}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <nav className="hidden items-center gap-4 sm:flex">
          {user ? (
            <>
              <Link to="/complaints/new" className="text-sm font-medium text-slate-600 hover:text-brand-700">
                File a complaint
              </Link>
              <span className="text-sm text-slate-500">
                {user.name} <span className="text-slate-300">·</span>{' '}
                <span className="font-medium text-brand-700">{roleLabels[user.role] ?? user.role}</span>
              </span>
              <Button variant="outline" size="sm" onClick={handleLogout} loading={loggingOut}>
                Log out
              </Button>
            </>
          ) : (
            <>
              <Link to="/complaints/new" className="text-sm font-medium text-slate-600 hover:text-brand-700">
                File a complaint
              </Link>
              <Link to="/login" className="text-sm font-medium text-slate-600 hover:text-brand-700">
                Log in
              </Link>
              <Link to="/register">
                <Button size="sm">Register</Button>
              </Link>
            </>
          )}
        </nav>
      </div>

      {menuOpen && (
        <div className="border-t border-slate-100 px-4 py-3 sm:hidden">
          <div className="flex flex-col gap-3">
            <Link to="/complaints/new" onClick={() => setMenuOpen(false)} className="text-sm font-medium text-slate-700">
              File a complaint
            </Link>
            {user ? (
              <>
                <span className="text-sm text-slate-500">
                  {user.name} · {roleLabels[user.role] ?? user.role}
                </span>
                <Button variant="outline" size="sm" onClick={handleLogout} loading={loggingOut}>
                  Log out
                </Button>
              </>
            ) : (
              <>
                <Link to="/login" onClick={() => setMenuOpen(false)} className="text-sm font-medium text-slate-700">
                  Log in
                </Link>
                <Link to="/register" onClick={() => setMenuOpen(false)}>
                  <Button size="sm" className="w-full">
                    Register
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
