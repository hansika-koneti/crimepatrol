import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useAppStore } from '@/store'
import {
  fetchAreas, fetchHighRisk, fetchHeatmap, runPrediction,
  fetchDailyBriefings, fetchPredictionHistory,
} from '@/services/api'
import MetricCard from '@/components/panels/MetricCard'
import XAIPanel from '@/components/panels/XAIPanel'
import RecommendationPanel from '@/components/panels/RecommendationPanel'
import RiskTrendChart from '@/components/charts/RiskTrendChart'
import CrimeTypeChart from '@/components/charts/CrimeTypeChart'
import { RISK_META, type RiskLevel } from '@/utils/constants'

const CARD_VARIANTS = {
  hidden: { opacity: 0, y: 20 },
  show:   { opacity: 1, y: 0 },
}

const STAGGER = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } }

export default function DashboardPage() {
  const {
    areas, setAreas, predictions, setPrediction,
    activePrediction, setActivePrediction,
    recommendations, setRecommendations,
    briefings, setBriefings,
    heatmapData, setHeatmapData,
    selectedAreaId, setSelectedAreaId,
    isRunningPrediction, setIsRunningPrediction,
  } = useAppStore()

  const [highRisk, setHighRisk] = useState<any[]>([])
  const [history, setHistory] = useState<any[]>([])
  const [error, setError] = useState('')
  const [loadingInit, setLoadingInit] = useState(true)

  // ── Initial data load ──────────────────────────────────────────────────────
  useEffect(() => {
    ;(async () => {
      try {
        const [areasData, highRiskData, briefingData, heatmap] = await Promise.all([
          fetchAreas(),
          fetchHighRisk(10),
          fetchDailyBriefings(),
          fetchHeatmap(),
        ])
        setAreas(areasData)
        setHighRisk(highRiskData)
        setBriefings(briefingData)
        setHeatmapData(heatmap)
        // Seed predictions store from high-risk list
        highRiskData.forEach((item: any) => {
          if (item.area_id && item.risk_score !== undefined) {
            setPrediction(item.area_id, item)
          }
        })
      } catch (e: any) {
        setError(e.message)
      } finally {
        setLoadingInit(false)
      }
    })()
  }, [])

  // ── Run prediction ─────────────────────────────────────────────────────────
  const handleRunPrediction = useCallback(async () => {
    if (!selectedAreaId) return
    setIsRunningPrediction(true)
    setError('')
    try {
      const result = await runPrediction(selectedAreaId)
      setPrediction(selectedAreaId, result.prediction)
      setActivePrediction(result.prediction)
      if (result.recommendations) setRecommendations(result.recommendations)
      const hist = await fetchPredictionHistory(selectedAreaId, 20)
      setHistory(hist)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setIsRunningPrediction(false)
    }
  }, [selectedAreaId])

  // ── Derived metrics ────────────────────────────────────────────────────────
  const allPreds = Object.values(predictions)
  const avgRisk = allPreds.length
    ? allPreds.reduce((s, p) => s + p.risk_score, 0) / allPreds.length
    : 0
  const criticalCount = allPreds.filter(p => p.risk_level === 'CRITICAL').length
  const highCount = allPreds.filter(p => p.risk_level === 'HIGH').length

  const latestBriefing = briefings[0]

  // Build trend from history
  const trendData = history.slice(0, 7).reverse().map((h: any) => ({
    date: new Date(h.predicted_for ?? h.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    risk_score: h.risk_score ?? 0,
  }))

  // Crime type distribution from high risk areas
  const crimeTypeCounts: Record<string, number> = {}
  highRisk.forEach((p: any) => {
    if (p.crime_type) crimeTypeCounts[p.crime_type] = (crimeTypeCounts[p.crime_type] ?? 0) + 1
  })
  const crimeChartData = Object.entries(crimeTypeCounts).map(([name, count]) => ({ name, count }))

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Error banner */}
      {error && (
        <div style={{
          padding: '12px 16px', background: 'rgba(239,68,68,0.1)',
          border: '1px solid rgba(239,68,68,0.3)', borderRadius: 10,
          color: '#ef4444', fontSize: '0.82rem',
        }}>
          ⚠ {error}
        </div>
      )}

      {/* Latest briefing banner */}
      {latestBriefing && (
        <motion.div
          initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="glass-card"
          style={{
            padding: '16px 20px',
            background: 'linear-gradient(135deg, rgba(99,102,241,0.08), rgba(168,85,247,0.06))',
            borderColor: 'rgba(99,102,241,0.2)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 20 }}>📡</span>
            <div>
              <div style={{ fontSize: '0.68rem', color: 'var(--color-accent-light)', fontWeight: 700, letterSpacing: '0.1em', marginBottom: 2 }}>
                TODAY'S BRIEFING — {latestBriefing.city?.toUpperCase()}
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                {latestBriefing.summary_text}
              </div>
            </div>
            <div style={{ marginLeft: 'auto', textAlign: 'right', flexShrink: 0 }}>
              <div style={{
                fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.06em',
                color: RISK_META[latestBriefing.overall_risk_level as RiskLevel]?.color ?? '#94a3b8',
              }}>
                {latestBriefing.overall_risk_level} RISK
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginTop: 2 }}>
                {latestBriefing.highest_risk_area}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Metric Cards */}
      <motion.div
        variants={STAGGER} initial="hidden" animate="show"
        style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}
      >
        {[
          { label: 'Avg Risk Score', value: avgRisk, unit: '/100', icon: '📊', color: '#6366f1' },
          { label: 'Critical Areas', value: criticalCount, icon: '🔴', color: '#a855f7', trend: 'up' as const, trendValue: 'Needs immediate attention' },
          { label: 'High Risk Areas', value: highCount, icon: '⚠️', color: '#ef4444' },
          { label: 'Areas Monitored', value: areas.length, icon: '🗺', color: '#22c55e' },
        ].map((card, i) => (
          <motion.div key={i} variants={CARD_VARIANTS}>
            <MetricCard
              label={card.label}
              value={typeof card.value === 'number' ? parseFloat(card.value.toFixed(1)) : card.value}
              unit={card.unit}
              icon={card.icon}
              color={card.color}
              trend={card.trend}
              trendValue={card.trendValue}
            />
          </motion.div>
        ))}
      </motion.div>

      {/* Main grid: predict panel + charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 20 }}>

        {/* Left: area selector + run prediction */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="glass-card" style={{ padding: '20px 24px' }}>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 16 }}>
              🔮 Run Prediction
            </div>

            {/* Area selector */}
            <div style={{ marginBottom: 12 }}>
              <label style={{
                display: 'block', fontSize: '0.7rem', fontWeight: 600,
                color: 'var(--color-text-muted)', marginBottom: 6,
                textTransform: 'uppercase', letterSpacing: '0.07em',
              }}>
                Select Area
              </label>
              <select
                value={selectedAreaId ?? ''}
                onChange={e => setSelectedAreaId(e.target.value || null)}
                style={{
                  width: '100%', padding: '10px 12px',
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid var(--color-border)', borderRadius: 8,
                  color: 'var(--color-text-primary)', fontSize: '0.85rem',
                  cursor: 'pointer', outline: 'none',
                }}
              >
                <option value="">— Choose an area —</option>
                {areas.map(a => {
                  const pred = predictions[a.id]
                  return (
                    <option key={a.id} value={a.id}>
                      {a.name} {pred ? `(${pred.risk_score.toFixed(0)})` : ''}
                    </option>
                  )
                })}
              </select>
            </div>

            {/* Selected area info */}
            {selectedAreaId && predictions[selectedAreaId] && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
                padding: '8px 12px', borderRadius: 8,
                background: 'rgba(255,255,255,0.03)', border: '1px solid var(--color-border)',
              }}>
                <span style={{
                  fontSize: '0.75rem', fontWeight: 700,
                  color: RISK_META[predictions[selectedAreaId].risk_level]?.color,
                }}>
                  {RISK_META[predictions[selectedAreaId].risk_level]?.icon}{' '}
                  {RISK_META[predictions[selectedAreaId].risk_level]?.label} risk
                </span>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginLeft: 'auto' }}>
                  Score: {predictions[selectedAreaId].risk_score.toFixed(1)}
                </span>
              </div>
            )}

            <motion.button
              onClick={handleRunPrediction}
              disabled={!selectedAreaId || isRunningPrediction}
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
              style={{
                width: '100%', padding: '12px',
                background: (!selectedAreaId || isRunningPrediction)
                  ? 'rgba(99,102,241,0.35)'
                  : 'linear-gradient(135deg, #6366f1, #818cf8)',
                border: 'none', borderRadius: 10, color: '#fff',
                fontWeight: 700, fontSize: '0.88rem',
                cursor: (!selectedAreaId || isRunningPrediction) ? 'not-allowed' : 'pointer',
                boxShadow: '0 4px 16px rgba(99,102,241,0.3)',
              }}
            >
              {isRunningPrediction ? '⟳ Running AI prediction…' : '▶ Run Prediction'}
            </motion.button>
          </div>

          {/* High risk areas list */}
          <div className="glass-card" style={{ padding: '20px 24px', overflow: 'hidden' }}>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 14 }}>
              🔴 Top Risk Areas
            </div>
            {loadingInit ? (
              <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>Loading…</div>
            ) : highRisk.slice(0, 6).map((p: any, i) => {
              const area = areas.find(a => a.id === p.area_id)
              const meta = RISK_META[p.risk_level as RiskLevel]
              return (
                <motion.div
                  key={p.area_id ?? i}
                  initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  onClick={() => { setSelectedAreaId(p.area_id); setActivePrediction(p) }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0',
                    borderBottom: '1px solid var(--color-border)',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{
                    width: 28, height: 28, borderRadius: 8, background: `${meta?.color}18`,
                    border: `1px solid ${meta?.color}33`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '0.7rem', fontWeight: 800, color: meta?.color, flexShrink: 0,
                  }}>
                    {i + 1}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {area?.name ?? p.area_id}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: meta?.color, fontWeight: 600 }}>
                      {meta?.label}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 800, color: meta?.color, flexShrink: 0 }}>
                    {p.risk_score?.toFixed(0)}
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>

        {/* Right: charts + XAI/Recs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Charts row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div className="glass-card" style={{ padding: '20px 24px' }}>
              <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: 12, color: 'var(--color-text-secondary)' }}>
                📈 Risk Trend
              </div>
              <RiskTrendChart data={trendData} />
            </div>
            <div className="glass-card" style={{ padding: '20px 24px' }}>
              <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: 12, color: 'var(--color-text-secondary)' }}>
                🚨 Crime Types
              </div>
              <CrimeTypeChart data={crimeChartData} />
            </div>
          </div>

          {/* XAI + Recommendations */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <XAIPanel prediction={activePrediction} loading={isRunningPrediction} />
            <RecommendationPanel recommendations={recommendations} loading={isRunningPrediction} />
          </div>
        </div>
      </div>
    </div>
  )
}
