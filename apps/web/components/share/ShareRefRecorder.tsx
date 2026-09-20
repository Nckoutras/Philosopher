'use client'

import { useEffect } from 'react'

import { setShareRef } from '@/lib/shareRef'

// Writes the share reference when a live share renders.
//
// WHY A COMPONENT AND NOT A LINE IN THE PAGE. /s/[id] is a SERVER component —
// that is what gives the link its unfurl preview, and it is also why the page
// itself cannot touch localStorage. This is the smallest possible client island:
// it renders nothing, and its whole job is one write on mount.
//
// MOUNTED ONLY ON THE LIVE BRANCH. Not on a withdrawn share, not on an unknown
// id, not on the API-unreachable state. A reference to something already dead
// would be carried through a signup only to be rejected there, and would occupy
// a person's storage for thirty days to do it.

export default function ShareRefRecorder({ shareId }: { shareId: string }) {
  useEffect(() => {
    setShareRef(shareId)
  }, [shareId])

  return null
}
