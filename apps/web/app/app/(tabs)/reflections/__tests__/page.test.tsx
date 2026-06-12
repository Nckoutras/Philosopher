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
vi.mock('@/components/reflections/MirrorVerdictCard', () => ({
  default: () => <div data-testid="mirror-verdict-card" />,
}))
vi.mock('@/components/reflections/CouncilVerdictCard', () => ({
  default: () => <div data-testid="council-verdict-card" />,
}))
vi.mock('@/components/reflections/FilterPills', () => ({
  default: () => <div data-testid="filter-pills" />,
}))
vi.mock('@/components/reflections/DateGrouper', () => ({
  default: ({ label }: { label: string }) => <div data-testid="date-grouper">{label}</div>,
}))

const mockLoadFeed = vi.fn().mockResolvedValue(undefined)

const lineItem = {
  kind: 'line' as const,
  id: 'sl-1',
  message_id: 'm-1',
  persona_id: 'p-1',
  persona_slug: 'marcus-aurelius',
  persona_display_name: 'Marcus Aurelius',
  message_content: 'Test content',
  conversation_id: 'c-1',
  saved_at: new Date().toISOString(),
  source_type: 'manual_save',
}

const mirrorItem = {
  kind: 'mirror_verdict' as const,
  save_id: 'ms-1',
  mirror_id: 'mir-1',
  thread: 'You may be circling the same fear.',
  host_persona_slug: 'carl_jung',
  host_persona_name: 'Carl Jung',
  mirror_kind: 'weekly',
  saved_at: new Date().toISOString(),
}

const councilItem = {
  kind: 'council_verdict' as const,
  save_id: 'cs-1',
  session_id: 'sess-1',
  synthesis: 'The four agree only that you already know.',
  persona_slugs: ['niccolo_machiavelli', 'epictetus', 'sigmund_freud', 'simone_de_beauvoir'],
  created_at: new Date().toISOString(),
  saved_at: new Date().toISOString(),
}

beforeEach(() => {
  mockPush.mockClear()
  mockReplace.mockClear()
  mockLoadFeed.mockClear()
  useStore.setState({
    token: 'test-token',
    feedItems: [],
    feedLoading: false,
    feedError: null,
    loadReflectionsFeed: mockLoadFeed,
  })
  vi.spyOn(apiModule.api, 'getPersonas').mockResolvedValue([])
})

describe('ReflectionsPage', () => {
  it('redirects to /auth when no token', () => {
    useStore.setState({ token: null })
    render(<ReflectionsPage />)
    expect(mockReplace).toHaveBeenCalledWith('/auth?mode=signin')
  })

  it('renders page header with Reflections eyebrow and title', async () => {
    render(<ReflectionsPage />)
    await waitFor(() => {
      expect(screen.getByText('Reflections')).toBeTruthy()
      expect(screen.getByText('Your saved lines.')).toBeTruthy()
    })
  })

  it('renders EmptyReflections when feed is empty', async () => {
    render(<ReflectionsPage />)
    await waitFor(() => {
      expect(screen.getByTestId('empty-reflections')).toBeTruthy()
    })
  })

  it('does not render FilterPills when feed is empty', async () => {
    render(<ReflectionsPage />)
    await waitFor(() => {
      expect(screen.queryByTestId('filter-pills')).toBeNull()
    })
  })

  it('renders saved line cards and filter pills when feed has line items', async () => {
    useStore.setState({ feedItems: [lineItem], loadReflectionsFeed: mockLoadFeed })
    render(<ReflectionsPage />)
    await waitFor(() => {
      expect(screen.getByTestId('saved-line-card')).toBeTruthy()
      expect(screen.getByTestId('filter-pills')).toBeTruthy()
    })
  })

  it('renders mirror and council verdict cards alongside lines', async () => {
    useStore.setState({
      feedItems: [lineItem, mirrorItem, councilItem],
      loadReflectionsFeed: mockLoadFeed,
    })
    render(<ReflectionsPage />)
    await waitFor(() => {
      expect(screen.getByTestId('saved-line-card')).toBeTruthy()
      expect(screen.getByTestId('mirror-verdict-card')).toBeTruthy()
      expect(screen.getByTestId('council-verdict-card')).toBeTruthy()
    })
  })

  it('calls loadReflectionsFeed on mount', async () => {
    render(<ReflectionsPage />)
    await waitFor(() => {
      expect(mockLoadFeed).toHaveBeenCalledOnce()
    })
  })
})
