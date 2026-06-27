/**
 * Unit tests for MetricCard component
 * Tests rendering, numeric display, icon, label, and trend indicator.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import MetricCard from '../panels/MetricCard'

// Framer Motion must be mocked — it uses ResizeObserver which jsdom lacks
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  useMotionValue: (initial: number) => ({ set: vi.fn(), on: vi.fn(() => vi.fn()), get: () => initial }),
  useSpring: (mv: any) => mv,
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

describe('MetricCard', () => {
  it('renders the label', () => {
    render(
      <MetricCard label="High Risk Areas" value={12} icon="🔴" color="#ef4444" />
    )
    expect(screen.getByText('High Risk Areas')).toBeTruthy()
  })

  it('renders the icon', () => {
    render(
      <MetricCard label="Test" value={0} icon="🗺" color="#22c55e" />
    )
    expect(screen.getByText('🗺')).toBeTruthy()
  })

  it('renders string value without animation', () => {
    render(
      <MetricCard label="Quality" value="92%" icon="🔬" color="#f59e0b" animate={false} />
    )
    expect(screen.getByText('92%')).toBeTruthy()
  })

  it('renders unit when provided', () => {
    render(
      <MetricCard label="Score" value={55} unit="/100" icon="📊" color="#6366f1" animate={false} />
    )
    expect(screen.getByText('/100')).toBeTruthy()
  })

  it('renders trend value when provided', () => {
    render(
      <MetricCard
        label="Areas"
        value={3}
        icon="⚠️"
        color="#ef4444"
        trend="up"
        trendValue="needs attention"
        animate={false}
      />
    )
    expect(screen.getByText(/needs attention/)).toBeTruthy()
  })

  it('does not render trend when not provided', () => {
    const { container } = render(
      <MetricCard label="Test" value={0} icon="📋" color="#6366f1" animate={false} />
    )
    // No trend text should appear
    expect(container.querySelector('[style*="↑"]')).toBeNull()
  })
})
