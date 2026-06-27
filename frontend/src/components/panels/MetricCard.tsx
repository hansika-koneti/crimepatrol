import { motion } from 'framer-motion'
import { RISK_META, type RiskLevel } from '@/utils/constants'

interface Props {
  label: string
  value: string | number
  subtitle?: string
  riskLevel?: RiskLevel
  icon?: string
  trend?: number     // positive = up, negative = down
  loading?: boolean
}

export default function MetricCard({ label, value, subtitle, riskLevel, icon, trend, loading }: Props) {
  const meta = riskLevel ? RISK_META[riskLevel] : null

  return (
    <motion.div
      className="glass-card metric-glow"
      style={{ padding: '20px 24px' }}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          {label}
        </span>
        {icon && <span style={{ fontSize: 20, opacity: 0.7 }}>{icon}</span>}
      </div>

      {loading ? (
        <div style={{ height: 36, background: 'rgba(255,255,255,0.05)', borderRadius: 6, animation: 'pulse 1.5s infinite' }} />
      ) : (
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{
            fontSize: '2rem', fontWeight: 800,
            color: meta?.color ?? 'var(--color-text-primary)',
            lineHeight: 1,
          }}>
            {value}
          </span>
          {trend !== undefined && (
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: trend >= 0 ? '#ef4444' : '#22c55e' }}>
              {trend >= 0 ? '▲' : '▼'} {Math.abs(trend)}%
            </span>
          )}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
        {riskLevel && (
          <span className={`badge ${meta?.bg}`} style={{ color: meta?.color }}>
            {meta?.label}
          </span>
        )}
        {subtitle && (
          <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>{subtitle}</span>
        )}
      </div>
    </motion.div>
  )
}
