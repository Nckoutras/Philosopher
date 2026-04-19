import { NextRequest, NextResponse } from 'next/server'

// Routes that require authentication
const PROTECTED_PREFIXES = ['/app', '/admin']

// Routes that require at least pro plan (checked server-side via cookie hint)
// Full enforcement is on the API — this is just a redirect UX layer
const PRO_PREFIXES: string[] = []

// Routes accessible only when NOT authenticated
const AUTH_ONLY_ROUTES = ['/login', '/register']

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
      url.pathname = '/login'
      url.searchParams.set('next', pathname)
      return NextResponse.redirect(url)
    }
  }

  // Redirect authenticated users away from auth routes
  if (AUTH_ONLY_ROUTES.includes(pathname) && isAuthenticated) {
    const url = request.nextUrl.clone()
    url.pathname = '/app/dashboard'
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
