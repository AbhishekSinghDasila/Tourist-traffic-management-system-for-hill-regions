import { apiClient } from './client'
import type { BatchPredictionResponse, ModelInfoResponse, PredictionResponse } from '../types'

export async function predictDistrictToday(district: string, weather = 7.0): Promise<PredictionResponse> {
  const res = await apiClient.get<PredictionResponse>(`/api/v1/predict/crowd/${encodeURIComponent(district)}`, {
    params: { weather },
  })
  return res.data
}

export async function predictCustom(
  district: string,
  targetDate?: string,
  weatherScore = 7.0,
): Promise<PredictionResponse> {
  const res = await apiClient.post<PredictionResponse>('/api/v1/predict/crowd', {
    district,
    target_date: targetDate,
    weather_score: weatherScore,
  })
  return res.data
}

export async function predictAllDistricts(weather = 7.0): Promise<BatchPredictionResponse> {
  const res = await apiClient.get<BatchPredictionResponse>('/api/v1/predict/crowd/all', { params: { weather } })
  return res.data
}

export async function fetchModelInfo(): Promise<ModelInfoResponse> {
  const res = await apiClient.get<ModelInfoResponse>('/api/v1/predict/model/info')
  return res.data
}
