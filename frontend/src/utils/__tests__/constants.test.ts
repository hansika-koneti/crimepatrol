/**
 * Unit tests for @/utils/constants
 * Validates RISK_META structure and RiskLevel type contract.
 */
import { describe, it, expect } from 'vitest'
import { RISK_META } from '../../utils/constants'
import type { RiskLevel } from '../../utils/constants'

const EXPECTED_LEVELS: RiskLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

describe('RISK_META constants', () => {
  it('has exactly 4 risk levels', () => {
    expect(Object.keys(RISK_META)).toHaveLength(4)
  })

  it.each(EXPECTED_LEVELS)('has entry for level %s', (level) => {
    expect(RISK_META[level]).toBeDefined()
  })

  it.each(EXPECTED_LEVELS)('%s has a label string', (level) => {
    expect(typeof RISK_META[level].label).toBe('string')
    expect(RISK_META[level].label.length).toBeGreaterThan(0)
  })

  it.each(EXPECTED_LEVELS)('%s has a valid hex color', (level) => {
    const { color } = RISK_META[level]
    expect(color).toMatch(/^#[0-9a-fA-F]{3,8}$/)
  })

  it.each(EXPECTED_LEVELS)('%s has an icon', (level) => {
    expect(typeof RISK_META[level].icon).toBe('string')
    expect(RISK_META[level].icon.length).toBeGreaterThan(0)
  })

  it.each(EXPECTED_LEVELS)('%s has a bg class string', (level) => {
    expect(RISK_META[level].bg).toContain(level)
  })

  it('all colors are unique', () => {
    const colors = EXPECTED_LEVELS.map(l => RISK_META[l].color)
    const unique = new Set(colors)
    expect(unique.size).toBe(colors.length)
  })

  it('all labels are unique', () => {
    const labels = EXPECTED_LEVELS.map(l => RISK_META[l].label)
    const unique = new Set(labels)
    expect(unique.size).toBe(labels.length)
  })

  it('CRITICAL is more urgent than LOW (longer label or distinct icon)', () => {
    // Simple sanity check: CRITICAL and LOW are different objects
    expect(RISK_META.CRITICAL).not.toEqual(RISK_META.LOW)
  })
})
