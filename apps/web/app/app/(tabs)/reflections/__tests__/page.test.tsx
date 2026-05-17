// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import ReflectionsPage from '../page'
import * as apiModule from '@/lib/api'
import { useStore } from '@/lib/store'

const mockPush = vi.fn()
const mockReplace = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
}))

vi.mock('@/components/reflections/EmptyReflections', () => ({
  default: () => <div data-testid="empty-reflections" />,
}))
vi.mock('@/components/reflections/SavedLineCard', () => ({
  default: () => <div data-testid="saved-line-card" />,
}))
vi.mock('@/components/reflections/FilterPills', () => ({
  default: () => <div data-testid="filter-pills" />,
}))
vi.mock('@/components/reflections/DateGrouper', () => ({
  default: ({ label }: { label: string }) => <div data-testid="date-grouper">{label}</div>,
}))

const mockLoadSavedLines = vi.fn().mockResolvedValue(undefined)

beforeEach(() => {
  mockPush.mockClear()
  mockReplace.mockClear()
  mockLoadSavedLines.mockClear()
  useStore.setState({
    token: 'test-token',
    savedLines: [],
    savedLinesLoading: false,
    savedLinesError: null,
    freeSaveCount: 0,
    freeTierLimit: 3,
    loadSavedLines: mockLoadSavedLines,
  })
  vi.spyOn(apiModule.api, 'getPersonas').mockResolvedValue([])
})

describe('ReflectionsPage', () => {
  it('redirects to /auth when no token', () => {
    useStore.setState({ token: null })
    render(<ReflectionsPage />)
    expect(mockReplace).toHaveBeenCalledWith('/auth')
  })

  it('renders page header with Reflections eyebrow and title', async () => {
    render(<ReflectionsPage />)
    await waitFor(() => {
      expect(screen.getByText('Reflections')).toBeTruthy()
      expect(screen.getByText('Your saved lines.')).toBeTruthy()
    })
  })

  it('renders EmptyReflections when savedLines is empty', async () => {
    render(<ReflectionsPage />)
    await waitFor(() => {
      expect(screen.getByTestId('empty-reflections')).toBeTruthy()
    })
  })

  it('does not render FilterPills when savedLines is empty', async () => {
    render(<ReflectionsPage />)
    await waitFor(() => {
      expect(screen.queryByTestId('filter-pills')).toBeNull()
    })
  })

  it('renders saved line cards and filter pills when savedLines has items', async () => {
    useStore.setState({
      savedLines: [
        {
          id: 'sl-1',
          message_id: 'm-1',
          persona_id: 'p-1',
          persona_slug: 'marcus-aurelius',
          persona_display_name: 'Marcus Aurelius',
          message_content: 'Test content',
          conversation_id: 'c-1',
          saved_at: new Date().toISOString(),
          source_type: 'manual',
        },
      ],
      freeSaveCount: 1,
      loadSavedLines: mockLoadSavedLines,
    })
    render(<ReflectionsPage />)
    await waitFor(() => {
      expect(screen.getByTestId('saved-line-card')).toBeTruthy()
      expect(screen.getByTestId('filter-pills')).toBeTruthy()
    })
  })

  it('calls loadSavedLines on mount', async () => {
    render(<ReflectionsPage />)
    await waitFor(() => {
      expect(mockLoadSavedLines).toHaveBeenCalledOnce()
    })
  })
})
