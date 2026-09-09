import { apiClient } from './client'
import type { DensityListResponse, DistrictDensity } from '../types'

export async function fetchAllDensity(): Promise<DensityListResponse> {
  const res = await apiClient.get<DensityListResponse>('/api/v1/traffic/density')
  return res.data
}

export async function fetchDistrictDensity(district: string): Promise<DistrictDensity> {
  const res = await apiClient.get<DistrictDensity>(`/api/v1/traffic/density/${encodeURIComponent(district)}`)
  return res.data
}
