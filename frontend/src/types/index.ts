// Types mirror the pydantic schemas in each service exactly (field names,
// optionality) — see services/*/app/schemas/*.py. Keep in sync if the
// backend contracts change.

export type Role = 'tourist' | 'citizen' | 'police' | 'emergency_team' | 'admin'

// ---- auth-service ----------------------------------------------------

export interface UserPublic {
  id: string
  name: string
  phone: string
  email?: string | null
  role: Role
  district?: string | null
  station_id?: string | null
}

export interface AccessTokenResponse {
  access_token: string
  token_type: string
}

export interface RegisterPayload {
  name: string
  phone: string
  email?: string
  password: string
  role: 'tourist' | 'citizen'
  district?: string
}

export interface ApiErrorDetail {
  error_code?: string
  message?: string
}

// ---- traffic-service ---------------------------------------------------

export type RiskLevel = 'GREEN' | 'AMBER' | 'RED'

export interface DistrictDensity {
  district: string
  active_vehicles: number
  capacity: number
  percentage: number
  risk_level: RiskLevel
  cached: boolean
  as_of: string
}

export interface DensityListResponse {
  districts: DistrictDensity[]
  total_active_vehicles: number
}

// ---- complaint-service ---------------------------------------------------

export const COMPLAINT_CATEGORIES = [
  'NOISE_POLLUTION',
  'LITTERING',
  'DRUNK_DRIVING',
  'ILLEGAL_PARKING',
  'RASH_DRIVING',
  'DRUG_ABUSE',
  'HARASSMENT',
  'OVERCHARGING',
  'OTHER',
] as const
export type ComplaintCategory = (typeof COMPLAINT_CATEGORIES)[number]

export const COMPLAINT_STATUSES = [
  'PENDING',
  'ASSIGNED',
  'IN_PROGRESS',
  'RESOLVED',
  'CLOSED',
  'PENDING_REVIEW',
  'ARCHIVED',
] as const
export type ComplaintStatus = (typeof COMPLAINT_STATUSES)[number]

export interface ComplaintPublic {
  id: string
  status: ComplaintStatus
  category: ComplaintCategory
  created_at: string
}

export interface MediaPoliceView {
  id: string
  ocr_plate_text?: string | null
  ocr_confidence?: number | null
  media_type: string
}

export interface MediaAdminView extends MediaPoliceView {
  s3_key: string
  file_size?: number | null
  uploaded_at: string
}

export interface ComplaintPoliceView {
  id: string
  plate_number?: string | null
  vehicle_state?: string | null
  category: ComplaintCategory
  description?: string | null
  lat: number
  lng: number
  district?: string | null
  status: ComplaintStatus
  created_at: string
  media: MediaPoliceView[]
}

export interface ComplaintAdminView {
  id: string
  user_id: string
  plate_number?: string | null
  vehicle_state?: string | null
  category: ComplaintCategory
  description?: string | null
  lat: number
  lng: number
  district?: string | null
  assigned_station_id?: string | null
  status: ComplaintStatus
  flag_reason?: string | null
  created_at: string
  updated_at: string
  media: MediaAdminView[]
}

export interface StatusUpdatePayload {
  status: ComplaintStatus
  note?: string
}

// ---- alert-service ---------------------------------------------------

export const ALERT_TYPES = ['AMBULANCE', 'ACCIDENT', 'LANDSLIDE', 'FLOOD', 'FIRE', 'OTHER'] as const
export type AlertType = (typeof ALERT_TYPES)[number]

export type AlertStatus = 'ACTIVE' | 'RESOLVED' | 'CANCELLED'

export interface AlertPublic {
  id: string
  alert_type: AlertType
  description?: string | null
  lat: number
  lng: number
  district?: string | null
  radius_km: number
  status: AlertStatus
  recipients_notified: number
  created_at: string
}

export interface AlertCreatePayload {
  alert_type: AlertType
  description?: string
  lat: number
  lng: number
  district?: string
  radius_km?: number
}

export interface LocationUpdatePayload {
  lat: number
  lng: number
  district?: string
}

// ---- ml-service ---------------------------------------------------

export interface PredictionResponse {
  district: string
  target_date: string
  predicted_vehicles: number
  capacity: number
  capacity_pct: number
  risk_level: RiskLevel
  features_used: Record<string, number>
  model_version: string
  predicted_at: string
}

export interface BatchPredictionResponse {
  predictions: PredictionResponse[]
  total_districts: number
  high_risk_districts: string[]
}

export interface ModelInfoResponse {
  model_type: string
  is_ready: boolean
  features: string[]
  districts_supported: string[]
  training_info: Record<string, number>
}

// The hill districts the system knows about (mirrors ml-service's DISTRICTS
// dict). There's no dedicated "list districts" endpoint anywhere in the
// backend, so this fixed list backs the register/complaint district
// dropdowns; the map and prediction pages still source their live data
// from the traffic/ml services rather than this constant.
export const KNOWN_DISTRICTS = [
  'nainital',
  'mussoorie',
  'haridwar',
  'rishikesh',
  'ranikhet',
  'almora',
  'kedarnath',
  'badrinath',
  'shimla',
  'manali',
  'dharamsala',
] as const
