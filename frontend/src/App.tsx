import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { useAppStore } from '@/store'
import Sidebar from '@/components/layout/Sidebar'
import TopBar from '@/components/layout/TopBar'
import { useWebSocket } from '@/hooks/useWebSocket'

// Lazy-loaded pages for code splitting
const LoginPage     = lazy(() => import('@/pages/LoginPage'))
const DashboardPage = lazy(() => import('@/pages/DashboardPage'))
const MapPage       = lazy(() => import('@/pages/MapPage'))
const PredictPage   = lazy(() => import('@/pages/PredictPage'))
const ReportsPage   = lazy(() => import('@/pages/ReportsPage'))
const HealthPage    = lazy(() => import('@/pages/HealthPage'))

// ─── Page loader spinner ───────────────────────────────────────────────────────
function PageLoader() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', background: 'var(--color-bg-primary)',
    }}>
      <div style={{
        width: 40, height: 40, border: '3px solid var(--color-border)',
        borderTopColor: 'var(--color-accent)', borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

// ─── Protected Route ──────────────────────────────────────────────────────────
function RequireAuth() {
  const isAuthenticated = useAppStore(s => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <AppShell />
}

// ─── Main App Shell (sidebar + content area) ──────────────────────────────────
function AppShell() {
  const sidebarCollapsed = useAppStore(s => s.sidebarCollapsed)
  useWebSocket()   // establish live WS connection once authenticated

  const sidebarW = sidebarCollapsed ? 64 : 220

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--color-bg-primary)' }}>
      <Sidebar />
      <div style={{
        flex: 1,
        marginLeft: sidebarW,
        transition: 'margin-left 0.3s cubic-bezier(0.4,0,0.2,1)',
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        overflow: 'hidden',
      }}>
        <TopBar />
        <main style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

// ─── Root ─────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth />}>
            <Route path="/"        element={<DashboardPage />} />
            <Route path="/map"     element={<MapPage />} />
            <Route path="/predict" element={<PredictPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/health"  element={<HealthPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
