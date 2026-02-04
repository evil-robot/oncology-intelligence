import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const authPassword = process.env.BASIC_AUTH_PASSWORD

  // Skip auth if not configured
  if (!authPassword) {
    return NextResponse.next()
  }

  // Allow access to login page and auth API
  if (
    request.nextUrl.pathname === '/login' ||
    request.nextUrl.pathname.startsWith('/api/auth')
  ) {
    return NextResponse.next()
  }

  // Check for auth cookie
  const authCookie = request.cookies.get('violet_auth')

  if (authCookie?.value === 'authenticated') {
    return NextResponse.next()
  }

  // Redirect to login page
  return NextResponse.redirect(new URL('/login', request.url))
}

// Apply to all routes except static files
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}
