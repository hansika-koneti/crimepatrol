import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useAppStore } from '@/store'
import { fetchAreas, runPrediction, fetchPredictionHistory } from '@/services/api'
import XAIPanel from '@/components/panels/XAIPanel'
import RecommendationPanel from '@/components/panels/RecommendationPanel'
import ProbabilityRadar from '@/components/charts/ProbabilityRadar'
import RiskTrendChart from '@/components/charts/RiskTrendChart'
import { RISK_META, type RiskLevel } from '@/utils/constants'

export default function PredictPage() {
  const {
    areas, setAreas,
    selectedAreaId, setSelectedAreaId,
    activePrediction, setActivePrediction,
    recommendations, setRecommendations,
    predictions, setPrediction,
    isRunningPrediction, setIsRunningPrediction,
  } = useAppStore()

  const [history, setHistory] = useState<any[]>([])
  const [error, setError] = useState('')
  const [loadingAreas, setLoadingAreas] = useState(true)
  const [tab, setTab] = useState<'explain' | 'history'>('explain')

  useEffect(() => {
    if (areas.length === 0) {
      fetchAreas().then(data => { setAreas(data); setLoadingAreas(false) })
    } else {
      setLoadingAreas(false)
    }
  }, [])

  const handleRun = useCallback(async () => {
    if (!selectedAreaId) return
    setIsRunningPrediction(true)
    setError('')
    try {
      const result = await runPrediction(selectedAreaId)
      setPrediction(selectedAreaId, result.prediction)
      setActivePrediction(result.prediction)
      if (result.recommendations) setRecommendations(result.recommendations)
      const hist = await fetchPredictionHistory(selectedAreaId, 30)
      setHistory(hist)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setIsRunningPrediction(false)
    }
  }, [selectedAreaId])

  const trendData = history.slice(0, 10).reverse().map((h: any) => ({
    date: new Date(h.predicted_for ?? h.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    risk_score: h.risk_score ?? 0,
  }))

  const selectedArea = areas.find(a => a.id === selectedAreaId)

  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Header */}
      <div>
        <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800 }}>Prediction Workbench</h2>
        <p style={{ margin: '4px 0 0', color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
          Run AI crime-risk predictions for any monitored area
        </p>
      </div>

      {error && (
        <div style={{
          padding: '10px 14px', background: 'rgba(239,68,68,0.1)',
          border: '1px solid rgba(239,68,68,0.3)', borderRadius: 10,
          color: '#ef4444', fontSize: '0.82rem',
        }}>
          ⚠ {error}
        </div>
      )}

      {/* Control row */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div style={{ flex: '1 1 260px' }}>
          <label style={{
            display: 'block', fontSize: '0.68rem', fontWeight: 700,
            color: 'var(--color-text-muted)', marginBottom: 6,
            textTransform: 'uppercase', letterSpacing: '0.09em',
          }}>Area</label>
          <select
            disabled={loadingAreas}
            value={selectedAreaId ?? ''}
            onChange={e => setSelectedAreaId(e.target.value || null)}
            style={{
              width: '100%', padding: '11px 14px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--color-border)', borderRadius: 8,
              color: 'var(--color-text-primary)', fontSize: '0.88rem',
              cursor: 'pointer', outline: 'none',
            }}
          >
            <option value="">{loadingAreas ? 'Loading…' : '— Select an area —'}</option>
            {areas.map(a => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>

        <motion.button
          onClick={handleRun}
          disabled={!selectedAreaId || isRunningPrediction}
          whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
          style={{
            padding: '11px 28px',
            background: (!selectedAreaId || isRunningPrediction)
              ? 'rgba(99,102,241,0.35)'
              : 'linear-gradient(135deg, #6366f1, #818cf8)',
            border: 'none', borderRadius: 10, color: '#fff',
            fontWeight: 700, fontSize: '0.9rem',
            cursor: (!selectedAreaId || isRunningPrediction) ? 'not-allowed' : 'pointer',
            boxShadow: '0 4px 20px rgba(99,102,241,0.35)',
            flexShrink: 0,
          }}
        >
          {isRunningPrediction ? (
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                width: 14, height: 14, border: '2px solid rgba(255,255,255,0.3)',
                borderTopColor: '#fff', borderRadius: '50%',
                animation: 'spin 0.6s linear infinite', display: 'inline-block',
              }} />
              Running…
            </span>
          ) : '▶ Run Prediction'}
        </motion.button>
      </div>

      {/* Main panels */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Left: XAI + Radar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <XAIPanel prediction={activePrediction} loading={isRunningPrediction} />

          {activePrediction?.probability_dist && (
            <div className="glass-card" style={{ padding: '20px 24px' }}>
              <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: 4 }}>
                🎯 Probability Distribution
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginBottom: 12 }}>
                Radar chart of risk-level probabilities
              </div>
              <ProbabilityRadar probabilityDist={activePrediction.probability_dist} />
            </div>
          )}
        </div>

        {/* Right: Recommendations + History */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <RecommendationPanel recommendations={recommendations} loading={isRunningPrediction} />

          {/* Tabs */}
          <div className="glass-card" style={{ padding: '20px 24px' }}>
            <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '1px solid var(--color-border)', paddingBottom: 0 }}>
              {(['explain', 'history'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  style={{
                    padding: '8px 16px', border: 'none', background: 'transparent',
                    color: tab === t ? 'var(--color-accent-light)' : 'var(--color-text-muted)',
                    fontWeight: tab === t ? 700 : 500,
                    fontSize: '0.8rem', cursor: 'pointer',
                    borderBottom: `2px solid ${tab === t ? 'var(--color-accent)' : 'transparent'}`,
                    transition: 'all 0.15s', textTransform: 'capitalize',
                  }}
                >
                  {t === 'explain' ? '📈 Trend' : '📋 History'}
                </button>
              ))}
            </div>

            {tab === 'explain' && (
              <>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: 8 }}>
                  Last 10 predictions for {selectedArea?.name ?? 'this area'}
                </div>
                <RiskTrendChart data={trendData} />
              </>
            )}

            {tab === 'history' && (
              <div style={{ overflowY: 'auto', maxHeight: 260 }}>
                {history.length === 0 ? (
                  <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', textAlign: 'center', padding: '20px 0' }}>
                    No prediction history yet
                  </div>
                ) : history.map((h: any, i) => {
                  const meta = RISK_META[h.risk_level as RiskLevel]
                  return (
                    <div key={i} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '8px 0', borderBottom: '1px solid var(--color-border)',
                    }}>
                      <div>
                        <div style={{ fontSize: '0.78rem', fontWeight: 600 }}>
                          {new Date(h.predicted_for ?? h.created_at).toLocaleString()}
                        </div>
                        <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)' }}>
                          {h.crime_type?.replace(/_/g, ' ')}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 800, color: meta?.color }}>
                          {h.risk_score?.toFixed(1)}
                        </div>
                        <div style={{
                          fontSize: '0.62rem', fontWeight: 700, color: meta?.color,
                          background: `${meta?.color}14`, padding: '2px 6px', borderRadius: 4,
                        }}>
                          {h.risk_level}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
