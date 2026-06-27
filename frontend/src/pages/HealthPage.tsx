import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useAppStore } from '@/store'
import { fetchAgentStatus, fetchQualityReports, triggerETL } from '@/services/api'

const STATUS_COLORS: Record<string, string> = {
  completed:  '#22c55e',
  running:    '#6366f1',
  failed:     '#ef4444',
  pending:    '#f59e0b',
  skipped:    '#94a3b8',
}

const STATUS_ICONS: Record<string, string> = {
  completed:  '✓',
  running:    '⟳',
  failed:     '✕',
  pending:    '⏳',
  skipped:    '—',
}

function StatusDot({ status }: { status: string }) {
  const color = STATUS_COLORS[status.toLowerCase()] ?? '#94a3b8'
  const isRunning = status.toLowerCase() === 'running'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div
        className={isRunning ? 'pulse-dot' : ''}
        style={!isRunning ? {
          width: 8, height: 8, borderRadius: '50%', background: color,
        } : { background: color }}
      />
      <span style={{ fontSize: '0.75rem', fontWeight: 700, color }}>
        {STATUS_ICONS[status.toLowerCase()] ?? '?'} {status}
      </span>
    </div>
  )
}

export default function HealthPage() {
  const { agentLogs, setAgentLogs, qualityReports, setQualityReports } = useAppStore()
  const [loading, setLoading]       = useState(true)
  const [etlTriggering, setEtlTriggering] = useState(false)
  const [etlMsg, setEtlMsg]         = useState('')
  const [error, setError]           = useState('')

  useEffect(() => {
    ;(async () => {
      try {
        const [agents, quality] = await Promise.all([fetchAgentStatus(), fetchQualityReports()])
        setAgentLogs(agents)
        setQualityReports(quality)
      } catch (e: any) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const handleETL = async () => {
    setEtlTriggering(true)
    setEtlMsg('')
    try {
      await triggerETL()
      setEtlMsg('✓ ETL pipeline triggered successfully')
    } catch (e: any) {
      setEtlMsg(`⚠ ${e.message}`)
    } finally {
      setEtlTriggering(false)
    }
  }

  // Summary counts
  const completedCount = agentLogs.filter(l => l.status?.toLowerCase() === 'completed').length
  const failedCount    = agentLogs.filter(l => l.status?.toLowerCase() === 'failed').length
  const avgQuality     = qualityReports.length
    ? qualityReports.reduce((s, r) => s + (r.quality_score ?? 0), 0) / qualityReports.length
    : 0

  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>

      <div>
        <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800 }}>System Health</h2>
        <p style={{ margin: '4px 0 0', color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
          Agent pipeline status, ETL controls, and data quality overview
        </p>
      </div>

      {error && (
        <div style={{
          padding: '10px 14px', background: 'rgba(239,68,68,0.1)',
          border: '1px solid rgba(239,68,68,0.3)', borderRadius: 10,
          color: '#ef4444', fontSize: '0.82rem',
        }}>⚠ {error}</div>
      )}

      {/* Status summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14 }}>
        {[
          { label: 'Agent Runs',      value: agentLogs.length,  icon: '🤖', color: '#6366f1' },
          { label: 'Completed',       value: completedCount,    icon: '✅', color: '#22c55e' },
          { label: 'Failed',          value: failedCount,       icon: '❌', color: '#ef4444' },
          { label: 'Avg Data Quality',value: `${(avgQuality * 100).toFixed(0)}%`, icon: '🔬', color: '#f59e0b', noAnimate: true },
        ].map((card, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="glass-card"
            style={{ padding: '18px 20px', position: 'relative', overflow: 'hidden' }}
          >
            <div style={{
              position: 'absolute', top: -16, right: -16, width: 64, height: 64,
              borderRadius: '50%',
              background: `radial-gradient(circle, ${card.color}22 0%, transparent 70%)`,
              pointerEvents: 'none',
            }} />
            <div style={{ fontSize: 22, marginBottom: 8 }}>{card.icon}</div>
            <div style={{ fontSize: '1.6rem', fontWeight: 900, color: card.color, lineHeight: 1 }}>
              {card.value}
            </div>
            <div style={{
              fontSize: '0.68rem', color: 'var(--color-text-muted)',
              fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', marginTop: 4,
            }}>
              {card.label}
            </div>
          </motion.div>
        ))}
      </div>

      {/* ETL trigger */}
      <div className="glass-card" style={{ padding: '20px 24px' }}>
        <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 6 }}>⚙ ETL Pipeline</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: 16 }}>
          Manually trigger the Extract-Transform-Load data pipeline to refresh crime incident data.
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <motion.button
            onClick={handleETL}
            disabled={etlTriggering}
            whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
            style={{
              padding: '10px 24px',
              background: etlTriggering ? 'rgba(99,102,241,0.4)' : 'linear-gradient(135deg, #6366f1, #818cf8)',
              border: 'none', borderRadius: 10, color: '#fff',
              fontWeight: 700, fontSize: '0.88rem', cursor: etlTriggering ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 16px rgba(99,102,241,0.3)',
            }}
          >
            {etlTriggering ? '⟳ Triggering…' : '🚀 Trigger ETL'}
          </motion.button>
          {etlMsg && (
            <motion.span
              initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}
              style={{
                fontSize: '0.8rem', fontWeight: 600,
                color: etlMsg.startsWith('✓') ? '#22c55e' : '#ef4444',
              }}
            >
              {etlMsg}
            </motion.span>
          )}
        </div>
      </div>

      {/* Agent status table */}
      <div className="glass-card" style={{ padding: '20px 24px' }}>
        <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 16 }}>
          🤖 Agent Pipeline Runs
        </div>
        {loading ? (
          <div style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>Loading agent status…</div>
        ) : agentLogs.length === 0 ? (
          <div style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem', textAlign: 'center', padding: '20px 0' }}>
            No agent runs recorded yet
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr>
                  {['Agent', 'Status', 'Duration', 'Started', 'Error'].map(h => (
                    <th key={h} style={{
                      textAlign: 'left', padding: '8px 12px',
                      color: 'var(--color-text-muted)', fontWeight: 600, fontSize: '0.68rem',
                      textTransform: 'uppercase', letterSpacing: '0.08em',
                      borderBottom: '1px solid var(--color-border)',
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {agentLogs.map((log, i) => (
                  <motion.tr
                    key={i}
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--color-border)', fontWeight: 600 }}>
                      {log.agent_name}
                    </td>
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--color-border)' }}>
                      <StatusDot status={log.status} />
                    </td>
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)' }}>
                      {log.duration_ms != null ? `${(log.duration_ms / 1000).toFixed(2)}s` : '—'}
                    </td>
                    <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                      {log.started_at ? new Date(log.started_at).toLocaleString() : '—'}
                    </td>
                    <td style={{
                      padding: '10px 12px', borderBottom: '1px solid var(--color-border)',
                      color: log.error ? '#ef4444' : 'var(--color-text-muted)',
                      fontSize: '0.72rem', maxWidth: 200,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {log.error ?? '—'}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quality reports */}
      {qualityReports.length > 0 && (
        <div className="glass-card" style={{ padding: '20px 24px' }}>
          <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 16 }}>
            🔬 Data Quality by Source
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {qualityReports.map((r, i) => {
              const score = (r.quality_score ?? 0) * 100
              const color = score >= 80 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444'
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.06 }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 16,
                    padding: '12px 14px', borderRadius: 10,
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--color-border)',
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>{r.source}</div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)' }}>
                      {r.total_records?.toLocaleString()} records · {r.duplicates_removed?.toLocaleString()} duplicates removed
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ fontSize: '1.1rem', fontWeight: 900, color }}>{score.toFixed(0)}%</div>
                    <div style={{ fontSize: '0.62rem', color: 'var(--color-text-muted)', marginTop: 2 }}>quality score</div>
                  </div>
                  <div style={{ width: 80 }}>
                    <div className="progress-bar">
                      <motion.div
                        className="progress-fill"
                        initial={{ width: 0 }} animate={{ width: `${score}%` }}
                        transition={{ duration: 0.8, delay: i * 0.06 }}
                        style={{ background: color }}
                      />
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
