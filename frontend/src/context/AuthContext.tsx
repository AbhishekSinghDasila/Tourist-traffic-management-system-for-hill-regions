import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import axios from 'axios'
import { fetchMe, login as apiLogin, logout as apiLogout } from '../api/auth'
import { setAccessToken, setSessionExpiredHandler } from '../api/client'
import type { Role, UserPublic } from '../types'

interface AuthContextValue {
  user: UserPublic | null
  role: Role | null
  /** True only while the app is doing its initial silent-refresh-on-load check. */
  initializing: boolean
  login: (phone: string, password: string) => Promise<UserPublic>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null)
  const [initializing, setInitializing] = useState(true)

  const clearSession = useCallback(() => {
    setUser(null)
    setAccessToken(null)
  }, [])

  // On app load: the access token only ever lives in memory, so a reload
  // wipes it. Try the HttpOnly refresh cookie to silently resume a session.
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await axios.post<{ access_token: string }>('/api/v1/auth/refresh', null, {
          withCredentials: true,
        })
        if (cancelled) return
        setAccessToken(res.data.access_token)
        const me = await fetchMe()
        if (!cancelled) setUser(me)
      } catch {
        if (!cancelled) clearSession()
      } finally {
        if (!cancelled) setInitializing(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [clearSession])

  useEffect(() => {
    setSessionExpiredHandler(clearSession)
    return () => setSessionExpiredHandler(null)
  }, [clearSession])

  const login = useCallback(async (phone: string, password: string) => {
    await apiLogin(phone, password)
    const me = await fetchMe()
    setUser(me)
    return me
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiLogout()
    } finally {
      clearSession()
    }
  }, [clearSession])

  const refreshUser = useCallback(async () => {
    const me = await fetchMe()
    setUser(me)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ user, role: user?.role ?? null, initializing, login, logout, refreshUser }),
    [user, initializing, login, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
