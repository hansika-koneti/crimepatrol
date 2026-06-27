import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip,
} from 'recharts'
import { RISK_META, type RiskLevel } from '@/utils/constants'

interface Props {
  probabilityDist: Record<string, number>
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  const level = payload[0]?.payload?.level as RiskLevel
  const meta = RISK_META[level]
  return (
    <div style={{
      background: 'var(--color-bg-card)',
      border: '1px solid var(--color-border)',
      borderRadius: 8, padding: '8px 12px',
    }}>
      <div style={{ fontSize: '0.72rem', color: meta?.color ?? '#fff', fontWeight: 600 }}>
        {meta?.label ?? level}
      </div>
      <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
        {(payload[0].value * 100).toFixed(1)}%
      </div>
    </div>
  )
}

export default function ProbabilityRadar({ probabilityDist }: Props) {
  const data = Object.entries(probabilityDist).map(([level, prob]) => ({
    level,
    probability: prob,
    fullMark: 1,
  }))

  return (
    <ResponsiveContainer width="100%" height={200}>
      <RadarChart data={data}>
        <PolarGrid stroke="rgba(255,255,255,0.06)" />
        <PolarAngleAxis
          dataKey="level"
          tick={({ x, y, payload }: any) => {
            const meta = RISK_META[payload.value as RiskLevel]
            return (
              <text x={x} y={y} textAnchor="middle" dominantBaseline="central"
                fill={meta?.color ?? '#94a3b8'} fontSize={11} fontWeight={700}>
                {meta?.icon} {meta?.label}
              </text>
            )
          }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Radar
          name="probability" dataKey="probability"
          stroke="#6366f1" fill="#6366f1" fillOpacity={0.25} strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
