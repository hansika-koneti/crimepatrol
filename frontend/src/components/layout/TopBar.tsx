import { useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAppStore } from '@/store'

const PAGE_TITLES: Record<string, { label: string; description: string }> = {
  '/':        { label: 'Dashboard',     description: 'Overview & live predictions' },
  '/map':     { label: 'Live Map',      description: 'Real-time geographic risk view' },
  '/predict': { label: 'Predict',       description: 'Run & inspect AI predictions' },
  '/reports': { label: 'Reports',       description: 'Daily briefings & analytics' },
  '/health':  { label: 'System Health', description: 'Agent status & data quality' },
}

export default function TopBar() {
  const location = useLocation()
  const { liveConnected } = useAppStore()
  const page = PAGE_TITLES[location.pathname] ?? { label: 'CrimePatrol', description: '' }

  return (
    <header style={{
      height: 60,
      background: 'var(--color-bg-secondary)',
      borderBottom: '1px solid var(--color-border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      backdropFilter: 'blur(12px)',
      flexShrink: 0,
    }}>
      {/* Left: page title */}
      <AnimatePresence mode="wait">
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 8 }}
          transition={{ duration: 0.2 }}
        >
          <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--color-text-primary)' }}>
            {page.label}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginTop: 1 }}>
            {page.description}
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Right: live status + time */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {/* Live badge */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '4px 12px',
          background: liveConnected ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
          border: `1px solid ${liveConnected ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.25)'}`,
          borderRadius: 20,
        }}>
          <div className={liveConnected ? 'pulse-dot' : ''}
            style={!liveConnected ? {
              width: 7, height: 7, borderRadius: '50%', background: '#ef4444',
            } : { background: '#22c55e' }}
          />
          <span style={{
            fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.08em',
            color: liveConnected ? '#22c55e' : '#ef4444',
          }}>
            {liveConnected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>

        {/* City pill */}
        <div style={{
          padding: '4px 12px',
          background: 'rgba(99,102,241,0.08)',
          border: '1px solid rgba(99,102,241,0.2)',
          borderRadius: 20,
          fontSize: '0.7rem',
          color: 'var(--color-accent-light)',
          fontWeight: 600,
          letterSpacing: '0.06em',
        }}>
          ⚡ CrimePatrol
        </div>
      </div>
    </header>
  )
}
