import { NextRequest, NextResponse } from 'next/server'

// Routes that require authentication
const PROTECTED_PREFIXES = ['/app', '/admin']

// Routes that require at least pro plan (checked server-side via cookie hint)
// Full enforcement is on the API — this is just a redirect UX layer
const PRO_PREFIXES: string[] = []

// Routes accessible only when NOT authenticated
const AUTH_ONLY_ROUTES = ['/auth']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Read token from cookie (set after login) or skip — API will enforce
  const token = request.cookies.get('ph_token')?.value
    ?? request.headers.get('authorization')?.replace('Bearer ', '')

  const isAuthenticated = !!token

  // Redirect unauthenticated users away from protected routes
  if (PROTECTED_PREFIXES.some((p) => pathname.startsWith(p))) {
    if (!isAuthenticated) {
      const url = request.nextUrl.clone()
      url.pathname = '/auth'
      // CLEAR BEFORE SETTING. clone() copies the whole URL, search included, so
      // overwriting only `pathname` left the protected route's own query dangling
      // on /auth -- a letter click arrived as /auth?src=email&mode=signin&next=...
      // where `src` meant nothing and was read by nobody. The destination's query
      // belongs inside `next`, not beside it.
      url.search = ''
      url.searchParams.set('mode', 'signin')
      // pathname + search, not pathname alone. The query IS the destination for a
      // letter: ?src=email is what lets the API write email_opened_at, and a
      // returnTo that drops it sends the reader to the right page as the wrong
      // kind of visit -- read_at without the attribution, which reads downstream
      // as organic in-app discovery. Read from `request.nextUrl`, which the line
      // above has not touched (`url` is a copy).
      url.searchParams.set('next', pathname + request.nextUrl.search)
      return NextResponse.redirect(url)
    }
  }

  // Redirect authenticated users away from auth routes
  if (AUTH_ONLY_ROUTES.includes(pathname) && isAuthenticated) {
    const url = request.nextUrl.clone()
    url.pathname = '/app/welcome'
    return NextResponse.redirect(url)
  }

  // Admin route — additional check (real enforcement is API-side)
  if (pathname.startsWith('/admin') && isAuthenticated) {
    // Allow through — API will return 403 if not admin
    return NextResponse.next()
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all paths except:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico
     * - public files
     * - api routes (handled by FastAPI)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
