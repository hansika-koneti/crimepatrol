import { create } from 'zustand'

// ─── Types ────────────────────────────────────────────────────────────────────
export interface Area {
  id: string
  name: string
  city: string
  centroid_lon: number | null
  centroid_lat: number | null
  population: number | null
  population_density: number | null
}

export interface Prediction {
  id?: string
  area_id: string
  risk_score: number
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  crime_type: string
  confidence: number
  predicted_for?: string
  explanation_text?: string
  top_features?: { feature: string; contribution: number; direction: string }[]
  probability_dist?: Record<string, number>
  similar_cases?: { date: string; area_name: string; outcome: string; similarity: number }[]
}

export interface Recommendation {
  action: string
  category: string
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  priority_score: number
  reason: string
  estimated_impact: string
}

export interface DailyBriefing {
  city: string
  briefing_date: string
  highest_risk_area: string
  highest_risk_score: number
  primary_crime_type: string
  overall_risk_level: string
  avg_risk_score: number
  summary_text: string
}

export interface AgentLog {
  run_id: string
  agent_name: string
  status: string
  duration_ms: number | null
  started_at: string | null
  error: string | null
}

export interface QualityReport {
  source: string
  quality_score: number
  total_records: number
  duplicates_removed: number
  run_at: string
}

// ─── Store ────────────────────────────────────────────────────────────────────
interface AppState {
  // Auth
  token: string | null
  isAuthenticated: boolean
  setToken: (token: string | null) => void

  // Data
  areas: Area[]
  setAreas: (areas: Area[]) => void

  selectedAreaId: string | null
  setSelectedAreaId: (id: string | null) => void

  predictions: Record<string, Prediction>   // keyed by area_id
  setPrediction: (areaId: string, pred: Prediction) => void

  activePrediction: Prediction | null
  setActivePrediction: (pred: Prediction | null) => void

  recommendations: Recommendation[]
  setRecommendations: (recs: Recommendation[]) => void

  briefings: DailyBriefing[]
  setBriefings: (briefings: DailyBriefing[]) => void

  agentLogs: AgentLog[]
  setAgentLogs: (logs: AgentLog[]) => void

  qualityReports: QualityReport[]
  setQualityReports: (reports: QualityReport[]) => void

  heatmapData: GeoJSON.FeatureCollection | null
  setHeatmapData: (data: GeoJSON.FeatureCollection | null) => void

  // UI
  isRunningPrediction: boolean
  setIsRunningPrediction: (v: boolean) => void

  liveConnected: boolean
  setLiveConnected: (v: boolean) => void

  sidebarCollapsed: boolean
  setSidebarCollapsed: (v: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  token: localStorage.getItem('cp_token'),
  isAuthenticated: !!localStorage.getItem('cp_token'),
  setToken: (token) => {
    if (token) localStorage.setItem('cp_token', token)
    else localStorage.removeItem('cp_token')
    set({ token, isAuthenticated: !!token })
  },

  areas: [],
  setAreas: (areas) => set({ areas }),

  selectedAreaId: null,
  setSelectedAreaId: (id) => set({ selectedAreaId: id }),

  predictions: {},
  setPrediction: (areaId, pred) =>
    set((s) => ({ predictions: { ...s.predictions, [areaId]: pred } })),

  activePrediction: null,
  setActivePrediction: (pred) => set({ activePrediction: pred }),

  recommendations: [],
  setRecommendations: (recommendations) => set({ recommendations }),

  briefings: [],
  setBriefings: (briefings) => set({ briefings }),

  agentLogs: [],
  setAgentLogs: (agentLogs) => set({ agentLogs }),

  qualityReports: [],
  setQualityReports: (qualityReports) => set({ qualityReports }),

  heatmapData: null,
  setHeatmapData: (heatmapData) => set({ heatmapData }),

  isRunningPrediction: false,
  setIsRunningPrediction: (v) => set({ isRunningPrediction: v }),

  liveConnected: false,
  setLiveConnected: (v) => set({ liveConnected: v }),

  sidebarCollapsed: false,
  setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
}))
