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
