import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer,
} from 'recharts'

interface DataPoint {
  name: string
  count: number
}

const COLORS = ['#6366f1', '#a855f7', '#ec4899', '#f59e0b', '#22c55e', '#06b6d4', '#ef4444']

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--color-bg-card)',
      border: '1px solid var(--color-border)',
      borderRadius: 8, padding: '8px 12px',
    }}>
      <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: 4 }}>
        {label?.replace(/_/g, ' ')}
      </div>
      <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-accent-light)' }}>
        {payload[0].value} incidents
      </div>
    </div>
  )
}

export default function CrimeTypeChart({ data }: { data: DataPoint[] }) {
  if (!data.length) return (
    <div style={{
      height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: 'var(--color-text-muted)', fontSize: '0.8rem',
    }}>
      No data available
    </div>
  )

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 9 }}
          angle={-35}
          textAnchor="end"
          tickFormatter={(v: string) => v.replace(/_/g, ' ').slice(0, 12)}
          interval={0}
        />
        <YAxis tick={{ fontSize: 10 }} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99,102,241,0.06)' }} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
