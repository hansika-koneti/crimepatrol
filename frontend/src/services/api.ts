import { API_BASE } from '@/utils/constants'
import { useAppStore } from '@/store'

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = useAppStore.getState().token
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> ?? {}),
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    useAppStore.getState().setToken(null)
    throw new Error('Session expired. Please log in again.')
  }
  const body = await res.json()
  if (!res.ok || !body.success) {
    throw new Error(body.errors?.[0]?.message ?? 'Request failed')
  }
  return body.data as T
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
export async function login(email: string, password: string): Promise<string> {
  const form = new URLSearchParams({ username: email, password })
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    body: form,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  if (!res.ok) throw new Error('Invalid credentials')
  const data = await res.json()
  return data.access_token as string
}

// ─── Areas ────────────────────────────────────────────────────────────────────
export const fetchAreas = () => request<any[]>('/areas')
export const fetchAreaPrediction = (id: string) => request<any>(`/areas/${id}/prediction`)

// ─── Predictions ──────────────────────────────────────────────────────────────
export const runPrediction = (areaId: string) =>
  request<any>('/predictions/run', {
    method: 'POST',
    body: JSON.stringify({ area_id: areaId }),
  })

export const fetchPredictionHistory = (areaId?: string, limit = 50) =>
  request<any[]>(`/predictions/history?limit=${limit}${areaId ? `&area_id=${areaId}` : ''}`)

export const fetchPrediction = (id: string) => request<any>(`/predictions/${id}`)

// ─── Analytics ────────────────────────────────────────────────────────────────
export const fetchHighRisk = (topN = 10) => request<any[]>(`/analytics/high-risk?top_n=${topN}`)
export const fetchHeatmap = () => request<any>('/analytics/heatmap')

// ─── Reports ─────────────────────────────────────────────────────────────────
export const fetchDailyBriefings = () => request<any[]>('/reports/daily')

// ─── Agents ───────────────────────────────────────────────────────────────────
export const fetchAgentStatus = () => request<any[]>('/agents/status')

// ─── Quality ──────────────────────────────────────────────────────────────────
export const fetchQualityReports = () => request<any[]>('/quality/reports')

// ─── ETL ──────────────────────────────────────────────────────────────────────
export const triggerETL = () => request<any>('/etl/trigger', { method: 'POST' })
