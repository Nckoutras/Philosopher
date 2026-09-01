// @vitest-environment node
//
// The web half of the taxonomy enforcement. The backend half is
// apps/api/tests/test_analytics_registry.py, under the same rule and checking
// the same two directions:
//
//   * every tracked literal in the app is declared in ANALYTICS_EVENTS
//   * every declared name has at least one call site
//
// Enforcement is a test, not a runtime guard, on purpose: an unknown event name
// must never throw inside a click handler. Analytics observes; it does not act.
//
// HOW THESE CAN FAIL. Adding a call with a new name fails the first test.
// Deleting the last caller of a declared name fails the second. Passing a
// computed name fails the third, which is what keeps the other two honest: a
// non-literal is invisible to a source scan.
//
// This scans source text rather than an AST because the repo has no TS parser
// dependency and adding one to ship a test would be a poor trade. Comments are
// stripped first — prose that mentions a call is not a call site, and the
// registry's own doc comment was the first thing this caught.
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { ANALYTICS_EVENTS } from '../analyticsEvents'

const WEB_ROOT = join(__dirname, '..', '..')
const SCAN_DIRS = ['app', 'components', 'lib']
const SKIP = new Set(['node_modules', '.next', '__tests__'])

function sourceFiles(dir: string): string[] {
  const out: string[] = []
  let entries: string[]
  try {
    entries = readdirSync(dir)
  } catch {
    return out
  }
  for (const entry of entries) {
    if (SKIP.has(entry)) continue
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      out.push(...sourceFiles(full))
    } else if (/\.(ts|tsx)$/.test(entry) && !/\.test\.tsx?$/.test(entry)) {
      out.push(full)
    }
  }
  return out
}

const FILES = SCAN_DIRS.flatMap((d) => sourceFiles(join(WEB_ROOT, d)))

function rel(file: string): string {
  return relative(WEB_ROOT, file).split('\\').join('/')
}

/**
 * Blank out comments while preserving offsets, so reported line numbers still
 * point at the original text.
 */
function stripComments(src: string): string {
  const blankKeepingNewlines = (m: string) => m.replace(/[^\n]/g, ' ')
  return src
    .replace(/\/\*[\s\S]*?\*\//g, blankKeepingNewlines)
    .replace(/(^|[^:'"])\/\/[^\n]*/g, (m, p1: string) => p1 + ' '.repeat(m.length - p1.length))
}

function lineOf(src: string, index: number): number {
  return src.slice(0, index).split('\n').length
}

function firedEvents(): Map<string, string[]> {
  const found = new Map<string, string[]>()
  for (const file of FILES) {
    const src = stripComments(readFileSync(file, 'utf8'))
    const re = /\btrack\(\s*(['"])([^'"]+)\1/g
    for (const m of src.matchAll(re)) {
      const name = m[2]
      const where = `${rel(file)}:${lineOf(src, m.index ?? 0)}`
      found.set(name, [...(found.get(name) ?? []), where])
    }
  }
  return found
}

describe('analytics registry', () => {
  it('scans a non-trivial number of source files', () => {
    // Guard on the guard: a broken walk would make every test below pass
    // vacuously by finding nothing at all.
    expect(FILES.length).toBeGreaterThan(50)
  })

  it('finds the call sites this PR added', () => {
    // Same purpose: proves the scanner sees real calls, so an empty result in
    // the tests below means "nothing wrong", not "nothing looked at".
    const fired = firedEvents()
    for (const name of ['landing_view', 'signup_started', 'first_reply_rendered', 'letter_action']) {
      expect(fired.get(name)?.length ?? 0).toBeGreaterThan(0)
    }
  })

  it('every fired event is declared', () => {
    const undeclared: Record<string, string[]> = {}
    for (const [name, sites] of firedEvents()) {
      if (!(name in ANALYTICS_EVENTS)) undeclared[name] = sites
    }
    expect(undeclared).toEqual({})
  })

  it('every declared event has a call site', () => {
    const fired = firedEvents()
    const orphans = Object.keys(ANALYTICS_EVENTS).filter((n) => !fired.has(n))
    // Declared-but-never-fired is what let the backend registry drift for
    // months: 15 aspirations and nothing checking. Delete, do not aspire.
    expect(orphans).toEqual([])
  })

  it('no call uses a computed event name', () => {
    const offenders: string[] = []
    for (const file of FILES) {
      // The analytics module defines track() itself; its own signature and its
      // internal debug call are not call sites.
      if (rel(file) === 'lib/analytics.ts') continue
      const src = stripComments(readFileSync(file, 'utf8'))
      const re = /\btrack\(\s*(?!['")])/g
      for (const m of src.matchAll(re)) {
        offenders.push(`${rel(file)}:${lineOf(src, m.index ?? 0)}`)
      }
    }
    expect(offenders).toEqual([])
  })

  it('declares no property name that suggests free text', () => {
    // A blunt guard on the privacy rule: properties are ids, enums, counts and
    // buckets. A property NAMED for content is the cheapest early signal that
    // content is about to be sent. Names only — values are asserted per call
    // site. A smoke alarm, not a lock.
    const banned = ['text', 'body', 'content', 'message', 'matter', 'email', 'title', 'excerpt']
    const offenders: string[] = []
    for (const [name, props] of Object.entries(ANALYTICS_EVENTS)) {
      for (const prop of props as readonly string[]) {
        // $current_url is a PostHog reserved property, not free text.
        if (prop.startsWith('$')) continue
        if (banned.some((b) => prop.includes(b))) offenders.push(`${name}.${prop}`)
      }
    }
    expect(offenders).toEqual([])
  })
})
