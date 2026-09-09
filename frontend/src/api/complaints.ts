import { apiClient } from './client'
import type {
  ComplaintAdminView,
  ComplaintCategory,
  ComplaintPoliceView,
  ComplaintPublic,
  StatusUpdatePayload,
} from '../types'

export interface SubmitComplaintInput {
  image: File
  category: ComplaintCategory
  description?: string
  lat: number
  lng: number
  district?: string
}

/**
 * NOTE ON THIS ENDPOINT: the backend's POST /api/v1/complaints route is
 * gated with require_role("citizen", "police", "admin", "emergency_team")
 * (services/complaint-service/app/routes/complaint.py) — it needs a valid
 * access token, and "tourist" is not in the allowed-role list. That is NOT
 * anonymous/no-auth, despite the docstring's "complainant identity is never
 * SENT TO POLICE" language (identity is still captured server-side, just
 * withheld from the police-facing view). The UI below reflects the code as
 * written: it requires login, and surfaces the 403 a tourist account would
 * get back rather than silently hiding the feature.
 */
export async function submitComplaint(input: SubmitComplaintInput): Promise<ComplaintPublic> {
  const form = new FormData()
  form.set('image', input.image)
  form.set('category', input.category)
  if (input.description) form.set('description', input.description)
  form.set('lat', String(input.lat))
  form.set('lng', String(input.lng))
  if (input.district) form.set('district', input.district)

  const res = await apiClient.post<ComplaintPublic>('/api/v1/complaints', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function fetchMyComplaints(limit = 20, offset = 0): Promise<ComplaintPublic[]> {
  const res = await apiClient.get<ComplaintPublic[]>('/api/v1/complaints/mine', { params: { limit, offset } })
  return res.data
}

export async function fetchStationComplaints(limit = 20, offset = 0): Promise<ComplaintPoliceView[]> {
  const res = await apiClient.get<ComplaintPoliceView[]>('/api/v1/complaints/station', { params: { limit, offset } })
  return res.data
}

export async function fetchComplaintAdminView(id: string): Promise<ComplaintAdminView> {
  const res = await apiClient.get<ComplaintAdminView>(`/api/v1/complaints/${id}/admin`)
  return res.data
}

export async function updateComplaintStatus(id: string, payload: StatusUpdatePayload): Promise<ComplaintPublic> {
  const res = await apiClient.patch<ComplaintPublic>(`/api/v1/complaints/${id}/status`, payload)
  return res.data
}

export interface ImageUrlEntry {
  media_id: string
  url: string | null
  expires_in?: number
  error?: string
}

export async function fetchComplaintImageUrls(id: string): Promise<{ complaint_id: string; images: ImageUrlEntry[] }> {
  const res = await apiClient.get(`/api/v1/complaints/${id}/image-url`)
  return res.data
}
