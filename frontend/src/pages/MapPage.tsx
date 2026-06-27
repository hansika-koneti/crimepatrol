import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAppStore } from '@/store'
import { fetchAreas, fetchHighRisk, fetchHeatmap } from '@/services/api'
import CrimeMap from '@/components/map/CrimeMap'
import { RISK_META, type RiskLevel } from '@/utils/constants'
import XAIPanel from '@/components/panels/XAIPanel'

export default function MapPage() {
  const {
    areas, setAreas, predictions, setPrediction, activePrediction, setActivePrediction,
    selectedAreaId, setSelectedAreaId, setHeatmapData,
  } = useAppStore()

  const [showHeatmap, setShowHeatmap] = useState(true)
  const [showPanel, setShowPanel] = useState(false)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<RiskLevel | 'ALL'>('ALL')
  const [search, setSearch] = useState('')

  useEffect(() => {
    ;(async () => {
      try {
        const [areasData, highRisk, heatmap] = await Promise.all([
          fetchAreas(),
          fetchHighRisk(50),
          fetchHeatmap(),
        ])
        setAreas(areasData)
        setHeatmapData(showHeatmap ? heatmap : null)
        highRisk.forEach((item: any) => {
          if (item.area_id) setPrediction(item.area_id, item)
        })
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const filteredAreas = areas.filter(a => {
    const pred = predictions[a.id]
    const matchFilter = filter === 'ALL' || pred?.risk_level === filter
    const matchSearch = a.name.toLowerCase().includes(search.toLowerCase())
    return matchFilter && matchSearch
  })

  const handleAreaClick = (areaId: string) => {
    setSelectedAreaId(areaId)
    const pred = predictions[areaId]
    if (pred) {
      setActivePrediction(pred)
      setShowPanel(true)
    }
  }

  const RISK_LEVELS: Array<RiskLevel | 'ALL'> = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 60px)', overflow: 'hidden', position: 'relative' }}>

      {/* Left panel: area list */}
      <div style={{
        width: 280, flexShrink: 0,
        background: 'var(--color-bg-secondary)',
        borderRight: '1px solid var(--color-border)',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Search + filter */}
        <div style={{ padding: '16px 16px 8px' }}>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search areas…"
            style={{
              width: '100%', padding: '9px 12px', boxSizing: 'border-box',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--color-border)', borderRadius: 8,
              color: 'var(--color-text-primary)', fontSize: '0.82rem', outline: 'none',
              marginBottom: 10,
            }}
          />
          {/* Risk filter pills */}
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {RISK_LEVELS.map(level => {
              const meta = level !== 'ALL' ? RISK_META[level] : null
              const active = filter === level
              return (
                <button
                  key={level}
                  onClick={() => setFilter(level)}
                  style={{
                    padding: '3px 8px', borderRadius: 12, fontSize: '0.62rem', fontWeight: 700,
                    border: `1px solid ${active ? (meta?.color ?? 'var(--color-accent)') : 'var(--color-border)'}`,
                    background: active ? `${meta?.color ?? 'var(--color-accent)'}18` : 'transparent',
                    color: active ? (meta?.color ?? 'var(--color-accent-light)') : 'var(--color-text-muted)',
                    cursor: 'pointer',
                  }}
                >
                  {level === 'ALL' ? 'ALL' : `${meta?.icon} ${level}`}
                </button>
              )
            })}
          </div>
        </div>

        <div style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)', padding: '4px 16px 8px', letterSpacing: '0.06em' }}>
          {filteredAreas.length} AREAS
        </div>

        {/* Area list */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading ? (
            <div style={{ padding: 24, color: 'var(--color-text-muted)', fontSize: '0.82rem', textAlign: 'center' }}>
              Loading areas…
            </div>
          ) : filteredAreas.map((area, i) => {
            const pred = predictions[area.id]
            const meta = pred ? RISK_META[pred.risk_level] : null
            const isSelected = selectedAreaId === area.id

            return (
              <motion.div
                key={area.id}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                transition={{ delay: i * 0.02 }}
                onClick={() => handleAreaClick(area.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 16px',
                  cursor: 'pointer',
                  background: isSelected ? 'rgba(99,102,241,0.12)' : 'transparent',
                  borderLeft: isSelected ? '2px solid var(--color-accent)' : '2px solid transparent',
                  transition: 'all 0.15s',
                }}
                whileHover={{ background: 'rgba(255,255,255,0.04)' }}
              >
                {/* Risk dot */}
                <div style={{
                  width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                  background: meta?.color ?? '#475569',
                  boxShadow: meta ? `0 0 6px ${meta.color}66` : 'none',
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-primary)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {area.name}
                  </div>
                  {pred && (
                    <div style={{ fontSize: '0.65rem', color: meta?.color, fontWeight: 600, marginTop: 1 }}>
                      {meta?.label} · {pred.risk_score.toFixed(1)}
                    </div>
                  )}
                </div>
                {pred && (
                  <div style={{
                    fontSize: '0.75rem', fontWeight: 800, color: meta?.color,
                    background: `${meta?.color}14`, padding: '2px 6px', borderRadius: 6, flexShrink: 0,
                  }}>
                    {pred.risk_score.toFixed(0)}
                  </div>
                )}
              </motion.div>
            )
          })}
        </div>

        {/* Heatmap toggle */}
        <div style={{
          padding: '12px 16px', borderTop: '1px solid var(--color-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', fontWeight: 600 }}>
            Heat Overlay
          </span>
          <button
            onClick={() => setShowHeatmap(!showHeatmap)}
            style={{
              width: 36, height: 20, borderRadius: 10, border: 'none', cursor: 'pointer',
              background: showHeatmap ? 'var(--color-accent)' : 'rgba(255,255,255,0.1)',
              position: 'relative', transition: 'background 0.2s',
            }}
          >
            <div style={{
              position: 'absolute', top: 2, left: showHeatmap ? 18 : 2,
              width: 16, height: 16, borderRadius: '50%',
              background: '#fff', transition: 'left 0.2s',
            }} />
          </button>
        </div>
      </div>

      {/* Map fill */}
      <div style={{ flex: 1, position: 'relative' }}>
        <CrimeMap />

        {/* Slide-in detail panel */}
        <AnimatePresence>
          {showPanel && activePrediction && (
            <motion.div
              initial={{ x: '100%', opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: '100%', opacity: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              style={{
                position: 'absolute', top: 16, right: 16, bottom: 16,
                width: 320, zIndex: 1000, overflowY: 'auto',
              }}
            >
              <div style={{ position: 'relative' }}>
                <button
                  onClick={() => setShowPanel(false)}
                  style={{
                    position: 'absolute', top: -10, right: -10, zIndex: 10,
                    width: 28, height: 28, borderRadius: '50%',
                    background: 'var(--color-bg-card)', border: '1px solid var(--color-border)',
                    color: 'var(--color-text-muted)', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 14,
                  }}
                >✕</button>
                <XAIPanel prediction={activePrediction} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
