// API & WebSocket base URLs (from Vite env vars)
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
export const WS_BASE  = import.meta.env.VITE_WS_URL      ?? '/ws'

// Risk level metadata
export const RISK_META = {
  LOW:      { label: 'Low',      color: '#22c55e', bg: 'risk-bg-LOW',      icon: '🟢' },
  MEDIUM:   { label: 'Medium',   color: '#f59e0b', bg: 'risk-bg-MEDIUM',   icon: '🟡' },
  HIGH:     { label: 'High',     color: '#ef4444', bg: 'risk-bg-HIGH',     icon: '🔴' },
  CRITICAL: { label: 'Critical', color: '#a855f7', bg: 'risk-bg-CRITICAL', icon: '🟣' },
} as const

export type RiskLevel = keyof typeof RISK_META
