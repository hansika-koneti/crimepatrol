import { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { login } from '@/services/api'
import { useAppStore } from '@/store'

export default function LoginPage() {
  const { setToken } = useAppStore()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const token = await login(email, password)
      setToken(token)
      navigate('/')
    } catch (err: any) {
      setError(err.message ?? 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--color-bg-primary)',
      backgroundImage: `
        radial-gradient(ellipse 80% 60% at 50% 0%, rgba(99,102,241,0.12) 0%, transparent 70%),
        radial-gradient(ellipse 40% 40% at 20% 80%, rgba(168,85,247,0.06) 0%, transparent 60%)
      `,
    }}>
      {/* Decorative grid */}
      <div style={{
        position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none',
        backgroundImage: 'linear-gradient(rgba(99,102,241,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.04) 1px, transparent 1px)',
        backgroundSize: '48px 48px',
      }} />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: 400, padding: '0 20px' }}
      >
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{
            width: 64, height: 64, margin: '0 auto 16px',
            background: 'linear-gradient(135deg, #6366f1, #a855f7)',
            borderRadius: 20, display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 30, boxShadow: '0 0 40px rgba(99,102,241,0.3)',
          }}>⚡</div>
          <h1 className="gradient-text" style={{ margin: 0, fontSize: '1.8rem', fontWeight: 900, letterSpacing: '-0.02em' }}>
            CrimePatrol
          </h1>
          <p style={{ margin: '6px 0 0', color: 'var(--color-text-muted)', fontSize: '0.82rem', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
            AI Safety Analytics Platform
          </p>
        </div>

        {/* Card */}
        <div className="glass-card" style={{ padding: '32px 28px' }}>
          <h2 style={{ margin: '0 0 24px', fontWeight: 700, fontSize: '1.1rem' }}>Admin Sign In</h2>

          <form onSubmit={handleSubmit}>
            {[
              { id: 'email', label: 'Email', type: 'email', value: email, set: setEmail, placeholder: 'admin@city.gov' },
              { id: 'password', label: 'Password', type: 'password', value: password, set: setPassword, placeholder: '••••••••' },
            ].map(({ id, label, type, value, set, placeholder }) => (
              <div key={id} style={{ marginBottom: 16 }}>
                <label htmlFor={id} style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                  {label}
                </label>
                <input
                  id={id} type={type} value={value} onChange={e => set(e.target.value)}
                  placeholder={placeholder} required autoComplete={id}
                  style={{
                    width: '100%', padding: '11px 14px',
                    background: 'rgba(255,255,255,0.04)', border: '1px solid var(--color-border)',
                    borderRadius: 8, color: 'var(--color-text-primary)', fontSize: '0.9rem',
                    outline: 'none', boxSizing: 'border-box', transition: 'border-color 0.2s',
                  }}
                  onFocus={e => (e.target.style.borderColor = 'var(--color-accent)')}
                  onBlur={e => (e.target.style.borderColor = 'var(--color-border)')}
                />
              </div>
            ))}

            {error && (
              <div style={{
                padding: '10px 14px', marginBottom: 16, background: 'rgba(239,68,68,0.1)',
                border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8,
                color: '#ef4444', fontSize: '0.8rem',
              }}>{error}</div>
            )}

            <motion.button
              type="submit" disabled={loading}
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              style={{
                width: '100%', padding: '13px',
                background: loading ? 'rgba(99,102,241,0.5)' : 'linear-gradient(135deg, #6366f1, #818cf8)',
                border: 'none', borderRadius: 10, color: '#fff',
                fontWeight: 700, fontSize: '0.9rem', cursor: loading ? 'not-allowed' : 'pointer',
                boxShadow: '0 4px 16px rgba(99,102,241,0.3)',
                transition: 'opacity 0.2s',
              }}
            >
              {loading ? '⟳ Authenticating…' : 'Sign In →'}
            </motion.button>
          </form>
        </div>

        <p style={{ textAlign: 'center', marginTop: 20, color: 'var(--color-text-muted)', fontSize: '0.7rem' }}>
          Single-admin dashboard · City-Agnostic AI Platform
        </p>
      </motion.div>
    </div>
  )
}
