import { useEffect, useRef } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'

interface Props {
  label: string
  value: number | string
  unit?: string
  icon: string
  color?: string
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  animate?: boolean
}

function AnimatedNumber({ target, decimals = 0 }: { target: number; decimals?: number }) {
  const mv = useMotionValue(0)
  const spring = useSpring(mv, { stiffness: 80, damping: 20, mass: 0.8 })
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => { mv.set(target) }, [target])

  useEffect(() => {
    return spring.on('change', (v) => {
      if (ref.current) ref.current.textContent = v.toFixed(decimals)
    })
  }, [spring, decimals])

  return <span ref={ref}>0</span>
}

const TREND_ICONS = { up: '↑', down: '↓', neutral: '→' }
const TREND_COLORS = { up: '#ef4444', down: '#22c55e', neutral: '#94a3b8' }

export default function MetricCard({
  label, value, unit, icon, color = '#6366f1', trend, trendValue, animate = true,
}: Props) {
  const isNumeric = typeof value === 'number'

  return (
    <motion.div
      className="glass-card metric-glow"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      style={{ padding: '20px 24px', position: 'relative', overflow: 'hidden' }}
    >
      {/* Background glow orb */}
      <div style={{
        position: 'absolute', top: -20, right: -20,
        width: 80, height: 80, borderRadius: '50%',
        background: `radial-gradient(circle, ${color}22 0%, transparent 70%)`,
        pointerEvents: 'none',
      }} />

      {/* Icon */}
      <div style={{
        width: 40, height: 40, borderRadius: 10, marginBottom: 12,
        background: `${color}18`,
        border: `1px solid ${color}33`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 18,
      }}>
        {icon}
      </div>

      {/* Value */}
      <div style={{
        fontSize: '1.9rem', fontWeight: 900, color, lineHeight: 1,
        letterSpacing: '-0.02em', marginBottom: 4, fontVariantNumeric: 'tabular-nums',
      }}>
        {animate && isNumeric
          ? <AnimatedNumber target={value as number} decimals={Number.isInteger(value) ? 0 : 1} />
          : value
        }
        {unit && (
          <span style={{ fontSize: '1rem', fontWeight: 600, marginLeft: 4, color: `${color}aa` }}>
            {unit}
          </span>
        )}
      </div>

      {/* Label */}
      <div style={{
        fontSize: '0.72rem', color: 'var(--color-text-muted)',
        fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4,
      }}>
        {label}
      </div>

      {/* Trend */}
      {trend && trendValue && (
        <div style={{
          fontSize: '0.68rem', color: TREND_COLORS[trend], fontWeight: 600,
        }}>
          {TREND_ICONS[trend]} {trendValue}
        </div>
      )}
    </motion.div>
  )
}
