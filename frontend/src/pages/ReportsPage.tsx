import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useAppStore } from '@/store'
import { fetchDailyBriefings, fetchQualityReports } from '@/services/api'
import { RISK_META, type RiskLevel } from '@/utils/constants'
import RiskTrendChart from '@/components/charts/RiskTrendChart'

export default function ReportsPage() {
  const { briefings, setBriefings, qualityReports, setQualityReports } = useAppStore()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedBriefing, setSelectedBriefing] = useState<any>(null)

  useEffect(() => {
    ;(async () => {
      try {
        const [b, q] = await Promise.all([fetchDailyBriefings(), fetchQualityReports()])
        setBriefings(b)
        setQualityReports(q)
        if (b.length) setSelectedBriefing(b[0])
      } catch (e: any) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  // Build trend from briefings
  const trendData = briefings.slice(0, 14).reverse().map((b: any) => ({
    date: new Date(b.briefing_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    risk_score: b.avg_risk_score ?? 0,
  }))

  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>

      <div>
        <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800 }}>Reports & Analytics</h2>
        <p style={{ margin: '4px 0 0', color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
          Daily AI briefings, risk trends, and data quality reports
        </p>
      </div>

      {error && (
        <div style={{
          padding: '10px 14px', background: 'rgba(239,68,68,0.1)',
          border: '1px solid rgba(239,68,68,0.3)', borderRadius: 10,
          color: '#ef4444', fontSize: '0.82rem',
        }}>⚠ {error}</div>
      )}

      {/* Risk trend chart */}
      {trendData.length > 0 && (
        <div className="glass-card" style={{ padding: '20px 24px' }}>
          <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 4 }}>📈 City Risk Trend</div>
          <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginBottom: 16 }}>
            Average risk score over last {trendData.length} days
          </div>
          <RiskTrendChart data={trendData} color="#a855f7" />
        </div>
      )}

      {/* Main grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Left: daily briefings list */}
        <div>
          <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 12, color: 'var(--color-text-secondary)' }}>
            📡 Daily Briefings
          </div>
          {loading ? (
            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>Loading…</div>
          ) : briefings.length === 0 ? (
            <div className="glass-card" style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>
              No briefings available yet
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {briefings.map((b: any, i) => {
                const meta = RISK_META[b.overall_risk_level as RiskLevel]
                const isSelected = selectedBriefing?.briefing_date === b.briefing_date
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    onClick={() => setSelectedBriefing(b)}
                    className="glass-card"
                    style={{
                      padding: '16px 18px', cursor: 'pointer',
                      borderColor: isSelected ? 'rgba(99,102,241,0.3)' : undefined,
                      background: isSelected ? 'rgba(99,102,241,0.06)' : undefined,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                        {new Date(b.briefing_date).toLocaleDateString('en-US', {
                          weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
                        })}
                      </div>
                      <span style={{
                        fontSize: '0.65rem', fontWeight: 700, color: meta?.color,
                        background: `${meta?.color}18`, padding: '2px 8px', borderRadius: 10,
                      }}>
                        {meta?.icon} {b.overall_risk_level}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', fontWeight: 700, marginBottom: 4 }}>
                      {b.city} — Avg: {b.avg_risk_score?.toFixed(1)}/100
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
                      {b.summary_text?.slice(0, 120)}{b.summary_text?.length > 120 ? '…' : ''}
                    </div>
                  </motion.div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right: selected briefing detail + quality table */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {selectedBriefing && (
            <div className="glass-card" style={{ padding: '20px 24px' }}>
              <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 16 }}>
                Briefing Detail
              </div>
              {[
                { label: 'Date', value: new Date(selectedBriefing.briefing_date).toLocaleDateString() },
                { label: 'City', value: selectedBriefing.city },
                { label: 'Highest Risk Area', value: selectedBriefing.highest_risk_area },
                { label: 'Highest Risk Score', value: selectedBriefing.highest_risk_score?.toFixed(1) },
                { label: 'Primary Crime Type', value: selectedBriefing.primary_crime_type?.replace(/_/g, ' ') },
                { label: 'Overall Risk', value: selectedBriefing.overall_risk_level },
              ].map(({ label, value }) => (
                <div key={label} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '8px 0', borderBottom: '1px solid var(--color-border)',
                  fontSize: '0.8rem',
                }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>{label}</span>
                  <span style={{ fontWeight: 600 }}>{value ?? '—'}</span>
                </div>
              ))}
              {selectedBriefing.summary_text && (
                <div style={{
                  marginTop: 16, padding: '12px 14px',
                  background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)',
                  borderRadius: 8,
                }}>
                  <div style={{ fontSize: '0.65rem', color: 'var(--color-accent-light)', marginBottom: 6, fontWeight: 700 }}>
                    ✦ SUMMARY
                  </div>
                  <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                    {selectedBriefing.summary_text}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Data Quality */}
          <div className="glass-card" style={{ padding: '20px 24px' }}>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 14 }}>
              🔬 Data Quality Reports
            </div>
            {qualityReports.length === 0 ? (
              <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', textAlign: 'center', padding: '16px 0' }}>
                No quality reports yet
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr>
                      {['Source', 'Quality', 'Records', 'Duplicates', 'Run At'].map(h => (
                        <th key={h} style={{
                          textAlign: 'left', padding: '6px 8px',
                          color: 'var(--color-text-muted)', fontWeight: 600, fontSize: '0.68rem',
                          textTransform: 'uppercase', letterSpacing: '0.07em',
                          borderBottom: '1px solid var(--color-border)',
                        }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {qualityReports.map((r: any, i) => (
                      <tr key={i}>
                        {[
                          r.source,
                          <span style={{
                            color: r.quality_score >= 0.8 ? '#22c55e' : r.quality_score >= 0.5 ? '#f59e0b' : '#ef4444',
                            fontWeight: 700,
                          }}>
                            {(r.quality_score * 100).toFixed(0)}%
                          </span>,
                          r.total_records?.toLocaleString(),
                          r.duplicates_removed?.toLocaleString(),
                          new Date(r.run_at).toLocaleString(),
                        ].map((v, j) => (
                          <td key={j} style={{
                            padding: '8px 8px', borderBottom: '1px solid var(--color-border)',
                            color: 'var(--color-text-secondary)',
                          }}>
                            {v}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
