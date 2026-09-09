import { apiClient } from './client'
import type { AlertCreatePayload, AlertPublic, LocationUpdatePayload } from '../types'

export async function fetchActiveAlerts(district?: string, limit = 20): Promise<AlertPublic[]> {
  const res = await apiClient.get<AlertPublic[]>('/api/v1/alerts', { params: { district, limit } })
  return res.data
}

export async function fetchAlertHistory(limit = 50): Promise<AlertPublic[]> {
  const res = await apiClient.get<AlertPublic[]>('/api/v1/alerts/history', { params: { limit } })
  return res.data
}

export async function fetchAlert(id: string): Promise<AlertPublic> {
  const res = await apiClient.get<AlertPublic>(`/api/v1/alerts/${id}`)
  return res.data
}

export async function triggerAlert(payload: AlertCreatePayload): Promise<AlertPublic> {
  const res = await apiClient.post<AlertPublic>('/api/v1/alerts', payload)
  return res.data
}

export async function cancelAlert(id: string, reason?: string): Promise<AlertPublic> {
  const res = await apiClient.patch<AlertPublic>(`/api/v1/alerts/${id}/cancel`, { reason })
  return res.data
}

export async function updateMyLocation(payload: LocationUpdatePayload): Promise<void> {
  await apiClient.post('/api/v1/alerts/location', payload)
}
