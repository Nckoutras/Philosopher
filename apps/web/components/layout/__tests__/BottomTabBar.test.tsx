// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import BottomTabBar from '../BottomTabBar'

const mockPush = vi.fn()
let mockPathname = '/app/library'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => mockPathname,
}))

beforeEach(() => {
  mockPush.mockClear()
  mockPathname = '/app/library'
})

describe('BottomTabBar', () => {
  it('renders all 4 tabs', () => {
    render(<BottomTabBar />)
    expect(screen.getByLabelText('Today')).toBeTruthy()
    expect(screen.getByLabelText('Rituals')).toBeTruthy()
    expect(screen.getByLabelText('Library')).toBeTruthy()
    expect(screen.getByLabelText('Account')).toBeTruthy()
  })

  it('marks Library tab as active on /app/library', () => {
    mockPathname = '/app/library'
    render(<BottomTabBar />)
    const libraryBtn = screen.getByLabelText('Library')
    expect(libraryBtn.getAttribute('aria-current')).toBe('page')
  })

  it('does not mark other tabs as active on /app/library', () => {
    mockPathname = '/app/library'
    render(<BottomTabBar />)
    expect(screen.getByLabelText('Today').getAttribute('aria-current')).toBeNull()
    expect(screen.getByLabelText('Rituals').getAttribute('aria-current')).toBeNull()
    expect(screen.getByLabelText('Account').getAttribute('aria-current')).toBeNull()
  })

  it('navigates to /app/library when Library tab tapped', () => {
    mockPathname = '/app/today'
    render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Library'))
    expect(mockPush).toHaveBeenCalledWith('/app/library')
  })

  it('navigates to /app/rituals when Rituals tab tapped', () => {
    mockPathname = '/app/today'
    render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Rituals'))
    expect(mockPush).toHaveBeenCalledWith('/app/rituals')
  })
})
