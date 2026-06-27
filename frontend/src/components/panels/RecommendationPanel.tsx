import { motion } from 'framer-motion'
import type { Recommendation } from '@/store'
import { RISK_META, type RiskLevel } from '@/utils/constants'

interface Props { recommendations: Recommendation[]; loading?: boolean }

const CATEGORY_ICONS: Record<string, string> = {
  patrol: '👮', infrastructure: '💡', alert: '📢', traffic: '🚦', cctv: '📷',
}

export default function RecommendationPanel({ recommendations, loading }: Props) {
  if (loading) return (
    <div className="glass-card" style={{ padding: 24 }}>
      <div style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>Loading recommendations…</div>
    </div>
  )

  const sorted = [...recommendations].sort((a, b) => b.priority_score - a.priority_score)

  return (
    <div className="glass-card" style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Recommendations</span>
        <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
          {recommendations.length} action{recommendations.length !== 1 ? 's' : ''}
        </span>
      </div>

      {sorted.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
          Run a prediction to generate recommendations
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {sorted.map((rec, i) => {
            const meta = RISK_META[rec.priority as RiskLevel]
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: `1px solid ${meta.color}22`,
                  borderLeft: `3px solid ${meta.color}`,
                  borderRadius: 10,
                  padding: '14px 16px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ fontSize: 18 }}>{CATEGORY_ICONS[rec.category] ?? '⚡'}</span>
                    <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {rec.action}
                    </span>
                  </div>
                  <span className={`badge ${meta.bg}`} style={{ color: meta.color, flexShrink: 0, marginLeft: 8 }}>
                    {rec.priority}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
                  {rec.reason}
                </p>
                <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                  <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', textTransform: 'capitalize' }}>
                    Category: {rec.category}
                  </span>
                  <span style={{ fontSize: '0.65rem', color: meta.color }}>
                    Impact: {rec.estimated_impact}
                  </span>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
