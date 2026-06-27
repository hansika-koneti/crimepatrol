import { motion } from 'framer-motion'
import { RISK_META, type RiskLevel } from '@/utils/constants'
import type { Prediction } from '@/store'

interface Props { prediction: Prediction | null; loading?: boolean }

export default function XAIPanel({ prediction, loading }: Props) {
  if (loading) return (
    <div className="glass-card" style={{ padding: 24 }}>
      <div style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>Loading explanation…</div>
    </div>
  )
  if (!prediction) return (
    <div className="glass-card" style={{ padding: 24, textAlign: 'center' }}>
      <div style={{ fontSize: '2rem', marginBottom: 8 }}>🔮</div>
      <div style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>Select an area and run a prediction</div>
    </div>
  )

  const meta = RISK_META[prediction.risk_level as RiskLevel]
  const features = prediction.top_features ?? []
  const maxContrib = Math.max(...features.map(f => f.contribution), 0.001)

  return (
    <div className="glass-card" style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>AI Explanation</span>
        <span className={`badge ${meta.bg}`} style={{ color: meta.color }}>
          {meta.icon} {meta.label}
        </span>
      </div>

      {/* Risk Score Gauge */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Risk Score</span>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: meta.color }}>
            {prediction.risk_score.toFixed(1)} / 100
          </span>
        </div>
        <div className="progress-bar">
          <motion.div
            className="progress-fill"
            initial={{ width: 0 }}
            animate={{ width: `${prediction.risk_score}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            style={{ background: `linear-gradient(90deg, ${meta.color}88, ${meta.color})` }}
          />
        </div>
      </div>

      {/* Confidence + Crime Type */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'Confidence', value: `${(prediction.confidence * 100).toFixed(1)}%` },
          { label: 'Crime Type', value: prediction.crime_type?.replace(/_/g, ' ') ?? '—' },
        ].map(({ label, value }) => (
          <div key={label} style={{
            background: 'rgba(255,255,255,0.04)', borderRadius: 8, padding: '10px 14px',
            border: '1px solid var(--color-border)',
          }}>
            <div style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.07em' }}>{label}</div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', textTransform: 'capitalize' }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Probability Distribution */}
      {prediction.probability_dist && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            Probability Distribution
          </div>
          {Object.entries(prediction.probability_dist).map(([level, prob]) => (
            <div key={level} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{ width: 60, fontSize: '0.72rem', color: RISK_META[level as RiskLevel]?.color ?? '#fff', fontWeight: 600 }}>{level}</span>
              <div className="progress-bar" style={{ flex: 1 }}>
                <motion.div className="progress-fill"
                  initial={{ width: 0 }} animate={{ width: `${prob * 100}%` }}
                  transition={{ duration: 0.7, delay: 0.1 }}
                  style={{ background: RISK_META[level as RiskLevel]?.color ?? '#6366f1' }}
                />
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', width: 40, textAlign: 'right' }}>
                {(prob * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Top SHAP Features */}
      {features.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            Top Contributing Factors
          </div>
          {features.map((f, i) => (
            <motion.div key={f.feature}
              initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }}
              style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}
            >
              <span style={{ fontSize: '0.65rem', color: f.direction === 'increases_risk' ? '#ef4444' : '#22c55e' }}>
                {f.direction === 'increases_risk' ? '▲' : '▼'}
              </span>
              <span style={{ flex: 1, fontSize: '0.75rem', color: 'var(--color-text-secondary)', textTransform: 'capitalize' }}>
                {f.feature.replace(/_/g, ' ')}
              </span>
              <div className="progress-bar" style={{ width: 80 }}>
                <div className="progress-fill" style={{
                  width: `${(f.contribution / maxContrib) * 100}%`,
                  background: f.direction === 'increases_risk' ? '#ef4444' : '#22c55e',
                }} />
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* LLM Explanation */}
      {prediction.explanation_text && (
        <div style={{
          background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.2)',
          borderRadius: 10, padding: '14px 16px',
        }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--color-accent-light)', marginBottom: 6, fontWeight: 600 }}>
            ✦ AI EXPLANATION
          </div>
          <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
            {prediction.explanation_text}
          </p>
        </div>
      )}

      {/* Similar Historical Cases */}
      {prediction.similar_cases && prediction.similar_cases.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            Similar Historical Cases
          </div>
          {prediction.similar_cases.map((c, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '8px 0', borderBottom: '1px solid var(--color-border)',
            }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                {new Date(c.date).toLocaleDateString()} · {c.area_name}
              </span>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className={`badge risk-bg-${c.outcome}`} style={{ color: RISK_META[c.outcome as RiskLevel]?.color }}>
                  {c.outcome}
                </span>
                <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)' }}>
                  {(c.similarity * 100).toFixed(0)}% match
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
