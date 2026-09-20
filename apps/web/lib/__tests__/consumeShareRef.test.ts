// @vitest-environment jsdom
/**
 * What both signup finish points do with a stored share reference.
 *
 * THE SECOND CLEARING CASE IS WHY THIS FILE EXISTS. Attributing a new account is
 * the obvious half and the half that gets written correctly. Clearing on a
 * RETURNING sign-in is the half nobody looks at, and it is the dangerous one: on
 * a shared device an uncleared reference sits waiting to credit a different
 * person's signup days later. It is asserted here first.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

const attributeShare = vi.fn()

vi.mock('@/lib/api', () => ({ api: { attributeShare: (...a: unknown[]) => attributeShare(...a) } }))

import { consumeShareRef } from '../consumeShareRef'
import { setShareRef, getShareRef } from '../shareRef'

const ID = 'AbCdEfGhIjKlMnOpQrStUv'

beforeEach(() => {
  localStorage.clear()
  attributeShare.mockReset()
  attributeShare.mockResolvedValue(undefined)
})
afterEach(() => vi.restoreAllMocks())

describe('a returning sign-in', () => {
  it('attributes nothing', async () => {
    setShareRef(ID)
    await consumeShareRef(false)
    expect(attributeShare).not.toHaveBeenCalled()
  })

  it('STILL clears the reference', async () => {
    // The one that matters. Left alive, this reference would credit whoever
    // signs up next in this browser — a different person, on a shared device,
    // days later.
    setShareRef(ID)
    await consumeShareRef(false)
    expect(getShareRef()).toBeNull()
  })
})

describe('a new account', () => {
  it('attributes it, once, with the stored id', async () => {
    setShareRef(ID)
    await consumeShareRef(true)
    expect(attributeShare).toHaveBeenCalledTimes(1)
    expect(attributeShare).toHaveBeenCalledWith(ID)
  })

  it('clears the reference after attributing', async () => {
    setShareRef(ID)
    await consumeShareRef(true)
    expect(getShareRef()).toBeNull()
  })

  it('clears it even when the call fails, and never throws', async () => {
    // A failed attribution costs a funnel row. A thrown error here would cost
    // the sign-in, and leaving the reference behind would let the failure retry
    // itself against an unrelated account later.
    attributeShare.mockRejectedValue(new Error('500'))
    setShareRef(ID)
    await expect(consumeShareRef(true)).resolves.toBeUndefined()
    expect(getShareRef()).toBeNull()
  })
})

describe('no reference', () => {
  it('does nothing at all', async () => {
    await consumeShareRef(true)
    expect(attributeShare).not.toHaveBeenCalled()
  })

  it('does not call the API for an expired one', async () => {
    localStorage.setItem(
      'wr_share_ref',
      JSON.stringify({ v: 1, id: ID, t: Date.now() - 31 * 24 * 60 * 60 * 1000 }),
    )
    await consumeShareRef(true)
    expect(attributeShare).not.toHaveBeenCalled()
  })
})
