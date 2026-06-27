import { NavLink, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAppStore } from '@/store'

const NAV = [
  { to: '/',         label: 'Dashboard',    icon: '⬡' },
  { to: '/map',      label: 'Live Map',     icon: '🗺' },
  { to: '/predict',  label: 'Predict',      icon: '🔮' },
  { to: '/reports',  label: 'Reports',      icon: '📋' },
  { to: '/health',   label: 'System Health',icon: '💊' },
]

export default function Sidebar() {
  const { sidebarCollapsed, setSidebarCollapsed, liveConnected, setToken } = useAppStore()
  const navigate = useNavigate()

  const logout = () => {
    setToken(null)
    navigate('/login')
  }

  return (
    <motion.aside
      animate={{ width: sidebarCollapsed ? 64 : 220 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      style={{
        background: 'var(--color-bg-secondary)',
        borderRight: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        padding: '16px 10px',
        position: 'fixed',
        top: 0, left: 0, bottom: 0,
        zIndex: 100,
        overflow: 'hidden',
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 4px 20px' }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10, flexShrink: 0,
          background: 'linear-gradient(135deg, #6366f1, #a855f7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 18, fontWeight: 800,
        }}>⚡</div>
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              style={{ lineHeight: 1.1 }}
            >
              <div style={{ fontWeight: 800, fontSize: '0.95rem', color: 'var(--color-text-primary)' }}>
                Crime<span style={{ color: 'var(--color-accent-light)' }}>Patrol</span>
              </div>
              <div style={{ fontSize: '0.62rem', color: 'var(--color-text-muted)', letterSpacing: '0.1em' }}>
                AI SAFETY PLATFORM
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Live status */}
      <AnimatePresence>
        {!sidebarCollapsed && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 12px', marginBottom: 12,
              background: liveConnected ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
              border: `1px solid ${liveConnected ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
              borderRadius: 8,
            }}
          >
            <div className={liveConnected ? 'pulse-dot' : ''}
              style={!liveConnected ? { width: 8, height: 8, borderRadius: '50%', background: '#ef4444' } : {}} />
            <span style={{ fontSize: '0.72rem', color: liveConnected ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
              {liveConnected ? 'LIVE' : 'OFFLINE'}
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Nav links */}
      <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {NAV.map(({ to, label, icon }) => (
          <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) =>
            `sidebar-link${isActive ? ' active' : ''}`
          }>
            <span style={{ fontSize: 16, flexShrink: 0 }}>{icon}</span>
            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.span
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                >
                  {label}
                </motion.span>
              )}
            </AnimatePresence>
          </NavLink>
        ))}
      </nav>

      {/* Bottom */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="sidebar-link"
          style={{ border: 'none', background: 'none', width: '100%', cursor: 'pointer' }}
        >
          <span style={{ fontSize: 14 }}>{sidebarCollapsed ? '→' : '←'}</span>
          <AnimatePresence>
            {!sidebarCollapsed && <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>Collapse</motion.span>}
          </AnimatePresence>
        </button>
        <button onClick={logout} className="sidebar-link" style={{ border: 'none', background: 'none', width: '100%', cursor: 'pointer', color: '#ef4444' }}>
          <span>⏻</span>
          <AnimatePresence>
            {!sidebarCollapsed && <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>Logout</motion.span>}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  )
}
