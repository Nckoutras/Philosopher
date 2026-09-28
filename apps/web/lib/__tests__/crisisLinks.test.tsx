// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { CRISIS_LINKS, linkifyCrisisText } from '../crisisLinks'

function links(text: string): Array<[string | null, string | null]> {
  const { container } = render(<p>{linkifyCrisisText(text)}</p>)
  return Array.from(container.querySelectorAll('a')).map((a) => [a.textContent, a.getAttribute('href')])
}

describe('linkifyCrisisText (SAFETY-003)', () => {
  it('keeps the text byte-identical — it only wraps, never rewrites', () => {
    const text = 'Call 112 now. Or 1018, or 10306. In the US, 988. UK: 116 123. See findahelpline.com.'
    const { container } = render(<p>{linkifyCrisisText(text)}</p>)
    expect(container.textContent).toBe(text)
  })

  it('links every approved resource, and only those', () => {
    expect(links('Call 112 now. Or 1018, or 10306. In the US, 988. UK: 116 123. See findahelpline.com.')).toEqual([
      ['112', 'tel:112'],
      ['1018', 'tel:1018'],
      ['10306', 'tel:10306'],
      ['988', 'tel:988'],
      ['116 123', 'tel:116123'],
      ['findahelpline.com', 'https://findahelpline.com'],
    ])
  })

  it('never links a number that merely contains an approved one', () => {
    expect(links('Room 1123, code 9880, 24 hours, 10306a, x112')).toEqual([])
  })

  it('links a resource at the very start and the very end', () => {
    expect(links('112')).toEqual([['112', 'tel:112']])
    expect(links('988 then findahelpline.com')).toEqual([
      ['988', 'tel:988'],
      ['findahelpline.com', 'https://findahelpline.com'],
    ])
  })

  it('handles two resources separated by a single space', () => {
    expect(links('112 1018')).toEqual([
      ['112', 'tel:112'],
      ['1018', 'tel:1018'],
    ])
  })

  it('dials without spaces (RFC 3966)', () => {
    for (const href of Object.values(CRISIS_LINKS)) {
      if (href.startsWith('tel:')) expect(href).not.toMatch(/\s/)
    }
  })

  it('returns plain text unchanged when there is nothing to link', () => {
    expect(linkifyCrisisText('no resources here')).toEqual(['no resources here'])
  })
})
