// STALE CONTENT POLICY
//
// This worker is network-first, and for anything that could carry auth state it
// is network-ONLY. It caches nothing that can go stale. The reasoning, route by
// route, because a future edit that widens the cache without reading this would
// reintroduce a security defect:
//
// 1. EVERY NAVIGATION IS NETWORK-ONLY — no exceptions, not a path list.
//    `apps/web/middleware.ts` runs on every navigation (its matcher excludes only
//    _next/static, _next/image, favicon.ico and image extensions). It reads the
//    `ph_token` cookie and issues 307 redirects: anything under /app or /admin
//    without the cookie goes to /auth, and /auth with the cookie goes to
//    /app/welcome. So the response to a navigation is a function of auth state at
//    request time. Caching an HTML body captured while signed in would replay a
//    signed-in shell to a signed-out browser; caching the redirect would strand a
//    signed-in user at /auth forever. That is true of EVERY route under the
//    middleware, not just /auth or /app/today — which is why the rule here is
//    `request.mode === 'navigate'` and not an enumerated path list. A new route
//    needs no change to this file.
//
// 2. THE API IS CROSS-ORIGIN, so the bypass is origin-based.
//    `lib/api.ts` points at https://philosopher-api-z9l9.onrender.com/api/v1 in
//    production; the /api/* rewrite in next.config.js is the local-dev path only.
//    A path-based `/api/**` rule would therefore match nothing in production and
//    give a false sense of coverage. Comparing origins covers the entire backend
//    surface in one rule — including the SSE streams, which must never be
//    intercepted by a worker.
//
// 3. ONLY IMMUTABLE ASSETS ARE CACHED.
//    /_next/static/** is content-hashed by the build; /icons/**, /personas/**,
//    /self-portrait/** and /insight_seal.webp are immutable assets replaced only
//    by a deploy that changes their name or ships a new worker version. Nothing
//    else is stored, ever.
//
// If the network is unavailable for a navigation or an API call, the browser's
// own error page is shown. That is correct behaviour: offline support is not a
// goal here — every screen in this app calls the API — and a stale OTP page or a
// stale token check would be a security defect, not a degraded experience.
//
// WHEN THIS COULD GO WRONG: if someone adds a path to PRECACHE_URLS or
// IMMUTABLE_PREFIXES that is not genuinely content-hashed or immutable, it will
// be served stale until the cache version below is bumped. Add a prefix only if
// its contents can never change under a fixed URL.

const CACHE_VERSION = 'v1'
const CACHE_NAME = `wise-room-static-${CACHE_VERSION}`

// Immutable, safe to serve from cache. See note 3 above before extending.
const IMMUTABLE_PREFIXES = [
  '/_next/static/',
  '/icons/',
  '/personas/',
  '/self-portrait/',
]

const IMMUTABLE_FILES = ['/insight_seal.webp']

// Warmed on install. Kept to the install-time icons: /_next/static/** filenames
// are build-hashed and cannot be enumerated from a static worker, so they are
// picked up at runtime by the immutable branch in fetch instead.
const PRECACHE_URLS = [
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/icon-192-maskable.png',
  '/icons/icon-512-maskable.png',
]

// Belt and braces alongside the origin check: never let a URL carrying a
// credential reach the cache, whatever its origin or mode.
const SENSITIVE_PATTERN = /token|otp|session/i

function isImmutable(pathname) {
  return (
    IMMUTABLE_PREFIXES.some((prefix) => pathname.startsWith(prefix)) ||
    IMMUTABLE_FILES.includes(pathname)
  )
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      // Individually, not addAll: one missing asset must not abort the install
      // and leave the app with no worker at all.
      Promise.allSettled(PRECACHE_URLS.map((url) => cache.add(url)))
    )
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
      )
      .then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event

  // Not a GET — never cached, never intercepted.
  if (request.method !== 'GET') return

  // Every navigation goes to the network. See note 1 above.
  if (request.mode === 'navigate') return

  let url
  try {
    url = new URL(request.url)
  } catch {
    return
  }

  // Cross-origin: the API, SSE streams, fonts. See note 2 above.
  if (url.origin !== self.location.origin) return

  // Anything that looks like it carries a credential.
  if (SENSITIVE_PATTERN.test(url.pathname) || SENSITIVE_PATTERN.test(url.search)) return

  // Immutable assets: cache-first, since the URL fully determines the bytes.
  if (isImmutable(url.pathname)) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response && response.ok && response.type === 'basic') {
              const copy = response.clone()
              caches.open(CACHE_NAME).then((cache) => cache.put(request, copy))
            }
            return response
          })
      )
    )
    return
  }

  // Everything else same-origin and non-navigational: network-first, falling
  // back to whatever happens to already be cached. Responses are not written to
  // the cache here — only the immutable branch above ever writes.
  event.respondWith(fetch(request).catch(() => caches.match(request)))
})
