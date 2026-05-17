// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SaveLineInlineUpgrade from '../SaveLineInlineUpgrade'
import { useStore } from '@/lib/store'

beforeEach(() => {
  useStore.setState({ freeSaveCount: 3, freeTierLimit: 3 })
})

describe('SaveLineInlineUpgrade', () => {
  it('renders locked copy with count', () => {
    render(<SaveLineInlineUpgrade onUpgrade={vi.fn()} onDismiss={vi.fn()} />)
    expect(
      screen.getByText("You've reached your free reflections (3 of 3)."),
    ).toBeTruthy()
  })

  it('renders body copy', () => {
    render(<SaveLineInlineUpgrade onUpgrade={vi.fn()} onDismiss={vi.fn()} />)
    expect(screen.getByText('Upgrade to Pro to keep saving.')).toBeTruthy()
  })

  it('renders Continue with Pro CTA', () => {
    render(<SaveLineInlineUpgrade onUpgrade={vi.fn()} onDismiss={vi.fn()} />)
    expect(screen.getByText('Continue with Pro')).toBeTruthy()
  })

  it('renders Maybe later CTA', () => {
    render(<SaveLineInlineUpgrade onUpgrade={vi.fn()} onDismiss={vi.fn()} />)
    expect(screen.getByText('Maybe later')).toBeTruthy()
  })

  it('calls onUpgrade when Continue with Pro tapped', () => {
    const onUpgrade = vi.fn()
    render(<SaveLineInlineUpgrade onUpgrade={onUpgrade} onDismiss={vi.fn()} />)
    fireEvent.click(screen.getByText('Continue with Pro'))
    expect(onUpgrade).toHaveBeenCalledOnce()
  })

  it('calls onDismiss when Maybe later tapped', () => {
    const onDismiss = vi.fn()
    render(<SaveLineInlineUpgrade onUpgrade={vi.fn()} onDismiss={onDismiss} />)
    fireEvent.click(screen.getByText('Maybe later'))
    expect(onDismiss).toHaveBeenCalledOnce()
  })
})
