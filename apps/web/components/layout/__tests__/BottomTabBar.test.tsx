// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import BottomTabBar from '../BottomTabBar'

let mockPathname = '/app/today'

vi.mock('next/navigation', () => ({
  // The bar navigates via <Link href>, not router.push. prefetch is here so the
  // idle route-warming effect can't throw if it fires.
  useRouter: () => ({ push: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => mockPathname,
}))

beforeEach(() => {
  mockPathname = '/app/today'
})

describe('BottomTabBar', () => {
  it('renders all 5 tabs', () => {
    render(<BottomTabBar />)
    expect(screen.getByLabelText('Home')).toBeTruthy()
    expect(screen.getByLabelText('Explore')).toBeTruthy()
    expect(screen.getByLabelText('Portrait')).toBeTruthy()
    expect(screen.getByLabelText('Account')).toBeTruthy()
    expect(screen.getByLabelText('Quotes')).toBeTruthy()
  })

  it('marks Portrait tab as active on /app/self-portrait', () => {
    mockPathname = '/app/self-portrait'
    render(<BottomTabBar />)
    const portraitBtn = screen.getByLabelText('Portrait')
    expect(portraitBtn.getAttribute('aria-current')).toBe('page')
  })

  it('does not mark other tabs as active on /app/self-portrait', () => {
    mockPathname = '/app/self-portrait'
    render(<BottomTabBar />)
    expect(screen.getByLabelText('Home').getAttribute('aria-current')).toBeNull()
    expect(screen.getByLabelText('Explore').getAttribute('aria-current')).toBeNull()
    expect(screen.getByLabelText('Account').getAttribute('aria-current')).toBeNull()
    expect(screen.getByLabelText('Quotes').getAttribute('aria-current')).toBeNull()
  })

  it('links the Quotes tab to /app/quotes', () => {
    render(<BottomTabBar />)
    expect(screen.getByLabelText('Quotes').getAttribute('href')).toBe('/app/quotes')
  })

  it('links the Explore tab to /app/explore', () => {
    render(<BottomTabBar />)
    expect(screen.getByLabelText('Explore').getAttribute('href')).toBe('/app/explore')
  })
})
