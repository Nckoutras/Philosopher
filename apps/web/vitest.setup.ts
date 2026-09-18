// Provide localStorage stub so Zustand persist middleware initialises in Node.js
const _storage: Record<string, string> = {}
Object.defineProperty(globalThis, 'localStorage', {
  value: {
    getItem: (key: string) => _storage[key] ?? null,
    setItem: (key: string, value: string) => { _storage[key] = value },
    removeItem: (key: string) => { delete _storage[key] },
    clear: () => { Object.keys(_storage).forEach((k) => { delete _storage[k] }) },
    get length() { return Object.keys(_storage).length },
    key: (_index: number) => null,
  } as Storage,
  configurable: true,
})

// jsdom does not implement Element.prototype.scrollIntoView — it is not a stub that
// returns undefined, it is absent, so calling it throws TypeError and React unmounts
// the tree. Any page that scrolls a sentinel into view on mount takes the whole
// render down with it.
//
// This surfaced when the stale mock in chat/conv/[id] was fixed (TD-86 step 2, cause
// 6). That page had never rendered in a test, so page.tsx:213-216 had never run. The
// repair did not cause the gap; it revealed it — the same corollary TD-45 states for
// assertions reached for the first time in months.
//
// Guarded on typeof because this setup file also runs for node-environment tests,
// where Element does not exist.
if (typeof Element !== 'undefined' && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() { /* no layout in jsdom */ }
}
