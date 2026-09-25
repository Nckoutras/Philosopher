// @vitest-environment node
//
// The build must not fetch fonts. next/font/google downloads every subset at
// build time and crashes on Google's extensionless /l/font?kit= URLs ("Cannot
// read properties of null (reading '1')", loader.js:112) — ~3% of CI builds, and
// Netlify production deploys run the same build. The fonts are self-hosted from
// app/fonts via next/font/local instead.
//
// A SOURCE ASSERTION, declared as one. The behavioural proof is a `next build`
// with the network blocked (PR narrative); this test keeps the decision from
// being undone by an innocent-looking import, which that build would only catch
// ~3% of the time.
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { join, extname } from 'node:path'

const WEB = join(__dirname, '..', '..')
const FONTS = join(WEB, 'app', 'fonts')

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name)
    if (name === 'node_modules' || name.startsWith('.')) return []
    if (statSync(p).isDirectory()) return sourceFiles(p)
    return ['.ts', '.tsx'].includes(extname(p)) && !p.includes('__tests__') ? [p] : []
  })
}

describe('fonts are self-hosted, so the build makes no font request', () => {
  it('no source file imports next/font/google', () => {
    const offenders = ['app', 'components', 'lib']
      .flatMap((d) => sourceFiles(join(WEB, d)))
      .filter((f) => /from ['"]next\/font\/google['"]/.test(readFileSync(f, 'utf8')))
    expect(offenders).toEqual([])
  })

  it('every font file the layout names exists and is a woff2', () => {
    const layout = readFileSync(join(WEB, 'app', 'layout.tsx'), 'utf8')
    const paths = [...layout.matchAll(/path: '\.\/fonts\/([^']+)'/g)].map((m) => m[1])
    expect(new Set(paths)).toEqual(new Set(['cormorant-garamond-latin.woff2', 'lora-latin.woff2']))
    for (const name of new Set(paths)) {
      const bytes = readFileSync(join(FONTS, name))
      expect(bytes.subarray(0, 4).toString('latin1')).toBe('wOF2')
    }
  })

  it('ships the OFL licence beside each font, as the licence requires', () => {
    for (const name of ['OFL-cormorantgaramond.txt', 'OFL-lora.txt']) {
      const p = join(FONTS, name)
      expect(existsSync(p)).toBe(true)
      expect(readFileSync(p, 'utf8')).toContain('SIL Open Font License, Version 1.1')
    }
  })
})
