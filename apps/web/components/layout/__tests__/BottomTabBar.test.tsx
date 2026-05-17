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

vi.mock('react-hot-toast', () => ({
  default: vi.fn(),
}))

import toast from 'react-hot-toast'

beforeEach(() => {
  mockPush.mockClear()
  vi.mocked(toast).mockClear()
  mockPathname = '/app/library'
})

describe('BottomTabBar', () => {
  it('renders all 4 tabs', () => {
    render(<BottomTabBar />)
    expect(screen.getByLabelText('Today')).toBeTruthy()
    expect(screen.getByLabelText('Reflections')).toBeTruthy()
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
    expect(screen.getByLabelText('Reflections').getAttribute('aria-current')).toBeNull()
    expect(screen.getByLabelText('Account').getAttribute('aria-current')).toBeNull()
  })

  it('navigates to /app/library when Library tab tapped', () => {
    mockPathname = '/app/today'
    render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Library'))
    expect(mockPush).toHaveBeenCalledWith('/app/library')
  })

  it('shows Coming soon toast when Today tab tapped', () => {
    render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Today'))
    expect(toast).toHaveBeenCalledWith('Coming soon', expect.any(Object))
    expect(mockPush).not.toHaveBeenCalled()
  })

  it('navigates to /app/reflections when Reflections tab tapped', () => {
    render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Reflections'))
    expect(mockPush).toHaveBeenCalledWith('/app/reflections')
    expect(toast).not.toHaveBeenCalled()
  })

  it('shows Coming soon toast when Account tab tapped', () => {
    render(<BottomTabBar />)
    fireEvent.click(screen.getByLabelText('Account'))
    expect(toast).toHaveBeenCalledWith('Coming soon', expect.any(Object))
  })
})
