import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

// In-memory only — deliberately never persisted to localStorage/sessionStorage.
// The refresh token lives in an HttpOnly cookie the browser manages for us;
// this module-level variable is the only place the access token exists on
// the client, and it's gone the moment the tab reloads (by design).
let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}

// Fired when a session can no longer be salvaged (refresh also failed).
// AuthProvider subscribes to this to clear user state and redirect to login,
// without this module needing to import React/router.
type SessionExpiredHandler = () => void
let onSessionExpired: SessionExpiredHandler | null = null
export function setSessionExpiredHandler(handler: SessionExpiredHandler | null): void {
  onSessionExpired = handler
}

export const apiClient = axios.create({
  baseURL: '/',
  withCredentials: true, // send/receive the HttpOnly refresh_token cookie
})

apiClient.interceptors.request.use((config) => {
  if (accessToken && !config.headers?.Authorization) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean
}

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  // Coalesce concurrent 401s into a single /refresh call.
  if (!refreshPromise) {
    refreshPromise = axios
      .post<{ access_token: string }>('/api/v1/auth/refresh', null, { withCredentials: true })
      .then((res) => {
        const token = res.data.access_token
        setAccessToken(token)
        return token
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined
    const status = error.response?.status
    const isRefreshCall = config?.url?.includes('/api/v1/auth/refresh')
    const isLoginCall = config?.url?.includes('/api/v1/auth/login')

    if (status === 401 && config && !config._retried && !isRefreshCall && !isLoginCall) {
      config._retried = true
      try {
        const token = await refreshAccessToken()
        config.headers = config.headers ?? {}
        config.headers.Authorization = `Bearer ${token}`
        return apiClient(config)
      } catch {
        setAccessToken(null)
        onSessionExpired?.()
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)

/** Extracts a human-readable message from the backend's {error_code, message} error shape. */
export function apiErrorMessage(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map(item => typeof item?.msg === 'string' ? item.msg : '').filter(Boolean).join('; ') || fallback
    }
    if (detail && typeof detail === 'object' && 'message' in detail && typeof detail.message === 'string') {
      return detail.message
    }
    if (err.code === 'ERR_NETWORK') {
      return 'Could not reach the server. Check your connection and try again.'
    }
    if (err.response?.status === 429) {
      return 'Too many requests — please slow down and try again shortly.'
    }
  }
  return fallback
}

export { refreshAccessToken }
