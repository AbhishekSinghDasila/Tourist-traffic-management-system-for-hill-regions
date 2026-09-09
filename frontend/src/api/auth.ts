import { apiClient, setAccessToken } from './client'
import type { AccessTokenResponse, RegisterPayload, UserPublic } from '../types'

/** Login uses OAuth2PasswordRequestForm on the backend: a urlencoded body
 * with fields literally named `username` (the phone number) and `password`. */
export async function login(phone: string, password: string): Promise<AccessTokenResponse> {
  const body = new URLSearchParams()
  body.set('username', phone)
  body.set('password', password)
  const res = await apiClient.post<AccessTokenResponse>('/api/v1/auth/login', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  setAccessToken(res.data.access_token)
  return res.data
}

export async function register(payload: RegisterPayload): Promise<UserPublic> {
  const res = await apiClient.post<UserPublic>('/api/v1/auth/register', payload)
  return res.data
}

export async function fetchMe(): Promise<UserPublic> {
  const res = await apiClient.get<UserPublic>('/api/v1/auth/me')
  return res.data
}

export async function logout(): Promise<void> {
  try {
    await apiClient.post('/api/v1/auth/logout')
  } finally {
    setAccessToken(null)
  }
}
